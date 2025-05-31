from django.db import models, transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.timezone import now
from fcm_django.models import FCMDevice
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from apps.notifications.services import (
    FirebaseNotificationService,
    UserNotificationService,
)
from apps.clients.models import UserProfile


class UserNotification(models.Model):
    user = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name="Usuario",
    )
    title = models.CharField(max_length=255, verbose_name="Título")
    message = models.TextField(verbose_name="Mensaje")
    is_read = models.BooleanField(default=False, verbose_name="Leída")
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Fecha de Creación"
    )
    read_at = models.DateTimeField(
        null=True, blank=True, verbose_name="Fecha de Lectura"
    )

    class Meta:
        verbose_name = "Notificación de usuario"
        verbose_name_plural = "Notificaciones de usuarios"
        ordering = ["-created_at"]

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = now()
            self.save()

    def __str__(self):
        return f"{self.title} - {'Leída' if self.is_read else 'No Leída'}"


class NotificationTemplate(models.Model):
    title = models.CharField(max_length=255, verbose_name="Título")
    body = models.TextField(verbose_name="Mensaje", max_length=255, null=True)
    created_at = models.DateField(auto_now_add=True, verbose_name="Fecha de Creación")
    send_at = models.DateField(
        default=now,
        verbose_name="Fecha de Envío Programada",
    )
    csv_file = models.FileField(
        upload_to="notifications/csv/",
        verbose_name="Archivo CSV",
        null=True,
        blank=True,
    )
    is_sent = models.BooleanField(default=False, verbose_name="¿Enviado?")

    class Meta:
        verbose_name = "Notificación masiva"
        verbose_name_plural = "Notificaciones masivas"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} - {self.send_at}"

    def clean(self):
        if self.csv_file and not self.csv_file.name.endswith(".csv"):
            raise ValidationError("Solo se permiten archivos CSV.")

    def process_csv_and_send_notifications(self):
        try:
            if self.csv_file:
                csv_file = self.csv_file.open("r")
                reader = csv.reader(csv_file)
                next(reader)  # Saltar la cabecera

                with transaction.atomic():
                    for row in reader:
                        email = row[0].strip()
                        user = UserProfile.objects.filter(email=email).first()
                        if user:
                            # En vez de enviar notificación directamente, creamos un PendingNotification
                            PendingNotification.objects.create(
                                notification=self,
                                sent_at=self.send_at,
                                device_id=(
                                    user.fcmdevice_set.first().registration_id
                                    if user.fcmdevice_set.exists()
                                    else None
                                ),
                            )

                csv_file.close()

            self.is_sent = True
            self.save()

        except Exception as e:
            raise ValidationError(f"Error procesando el archivo CSV: {str(e)}")

    def send_notification(self, user):
        UserNotificationService.create_notification(user, self.title, self.body)
        device = user.fcmdevice_set.filter(active=True).first()
        if device:
            FirebaseNotificationService.send_firebase_notification(
                device, self.title, self.body
            )

    def send_notification_to_all_users(self):
        fcm_devices = FCMDevice.objects.filter(active=True)
        with transaction.atomic():
            for device in fcm_devices:
                user = device.user
                if user:
                    self.send_notification(user)


@receiver(post_save, sender=NotificationTemplate)
def create_fmc_notifications(sender, instance, created, **kwargs):
    if created:
        fcm_devices = FCMDevice.objects.filter(active=True)
        pending_notifications = [
            PendingNotification(
                notification=instance,
                sent_at=instance.send_at,
                device_id=device.registration_id,
            )
            for device in fcm_devices
        ]

        batch_size = 1000
        for i in range(0, len(pending_notifications), batch_size):
            with transaction.atomic():
                PendingNotification.objects.bulk_create(
                    pending_notifications[i : i + batch_size]
                )


class PendingNotification(models.Model):
    notification = models.ForeignKey(
        NotificationTemplate,
        on_delete=models.CASCADE,
        related_name="logs",
        verbose_name="Notificación",
    )

    device_id = models.CharField(
        max_length=500, verbose_name="Dispositivo", blank=True, null=True
    )
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Envío")
    is_sent = models.BooleanField(default=False, verbose_name="Enviada")

    class Meta:
        verbose_name = "Notificación FCM"
        verbose_name_plural = "Notificaciones FCM"

    def __str__(self):
        return (
            f"{self.notification.title} - {'Enviada' if self.is_sent else 'Pendiente'}"
        )
