import time

from anyio import sleep
from django.core.management import BaseCommand
from django.utils import timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.db import transaction
import csv

from apps.notifications.models import PendingNotification
from apps.notifications.services import FirebaseNotificationService, UserNotificationService
from apps.clients.models import UserProfile, Transaction
from apps.clients.models import MassPointsLoad  # Importar el modelo de carga de puntos
from fcm_django.models import FCMDevice


class Command(BaseCommand):
    help = "Enviar notificaciones"

    def handle(self, *args, **options):
        self.send_notifications()
        self.process_mass_points_loads()

    def send_notifications(self):
        """ Procesar notificaciones pendientes y enviarlas """
        date = timezone.now()
        notifications = PendingNotification.objects.filter(is_sent=False, sent_at__day=date.day)

        for notification in notifications:
            token = notification.device_id
            title = f"{notification.notification.title}"
            body = f"{notification.notification.body}"
            try:
                FirebaseNotificationService.send_firebase_notification(token, title, body, None)
            except Exception as e:
                print("Error:: ", str(e))

            notification.is_sent = True
            notification.save()
            time.sleep(1)

    def process_mass_points_loads(self):
        """ Procesar las cargas masivas de puntos pendientes """
        today = timezone.now().date()
        pending_loads = MassPointsLoad.objects.filter(is_credited=False, assign_date=today)

        for load in pending_loads:
            try:
                if load.csv_file:
                    self.process_csv_file(load)
                else:
                    self.assign_points_to_all_users(load)

                load.is_credited = True
                load.save()

            except Exception as e:
                pass

    def process_csv_file(self, load):
        """ Procesar archivo CSV y asignar puntos """
        csv_file = load.csv_file.open("r")
        reader = csv.reader(csv_file)
        next(reader)  # Saltar la cabecera

        batch_size = 500
        batch = []
        max_workers = 10

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []

            for row in reader:
                email = row[0].strip()
                points = int(row[1].strip()) if len(row) > 1 else load.points_amount
                batch.append((email, points))

                if len(batch) >= batch_size:
                    futures.append(executor.submit(self.process_batch, batch, load))
                    batch = []

            if batch:
                futures.append(executor.submit(self.process_batch, batch, load))

            for future in as_completed(futures):
                future.result()  # Capturar errores

        csv_file.close()

    def process_batch(self, batch, load):
        """ Procesar un lote de asignaciones de puntos """
        with transaction.atomic():
            for email, points in batch:
                user = UserProfile.objects.filter(email=email).first()
                if user:
                    self.assign_points(user, points, load)

    def assign_points_to_all_users(self, load):
        """ Asignar puntos a todos los usuarios si no hay CSV """
        users = UserProfile.objects.filter(is_active=True)
        with transaction.atomic():
            for user in users:
                self.assign_points(user, load.points_amount, load)

    def assign_points(self, user, points, load):
        """ Asignar puntos a un usuario y generar transacción """
        user.points += points
        user.save()

        # Registrar transacción
        Transaction.objects.create(
            user=user,
            amount=points,
            status=0,  # Ingreso
            tipo="Internal",
            saldo=user.points,
            transaction_status="Completed",
            descripcion=f"{load.reason} - {load.title}"
        )

        # Crear notificación local
        UserNotificationService.create_notification(
            user,
            "Puntos acreditados",
            f"Se te han asignado {points} puntos con motivo de {load.title}."
        )

        # Enviar notificación push
        device = user.fcmdevice_set.first()
        if device and device.registration_id:
            FirebaseNotificationService.send_firebase_notification(
                device.registration_id,
                "Puntos acreditados",
                f"Se te han asignado {points} puntos con motivo de {load.title}.",
                data=None
            )
