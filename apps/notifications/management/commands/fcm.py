import firebase_admin
from django.core.management import BaseCommand
from fcm_django.models import FCMDevice
from firebase_admin import messaging

from apps.notifications.services import FirebaseNotificationService


class Command(BaseCommand):
    help = "Enviar notificaciones"

    def handle(self, *args, **options):
        # Enviar notificaciones
        token = FCMDevice.objects.all().first().registration_id
        title = f"Partido destacado"
        body = f"¡Portugal vs Dinamarca fue un gran partido!"
        FirebaseNotificationService.send_firebase_notification(token, title, body, None)



