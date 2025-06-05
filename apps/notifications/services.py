import firebase_admin
from fcm_django.models import FCMDevice
from firebase_admin import messaging, get_app


class FirebaseNotificationService:
    print(">>> Firebase apps cargadas:", list(firebase_admin._apps.keys()))

    @classmethod
    def send_firebase_notification(cls, target, title, body, data=None):
        try:
            if isinstance(target, str):
                device = FCMDevice.objects.filter(
                    registration_id=target, active=True
                ).first()
                if not device:
                    print(f"No device found for token {target}")
                    return
            else:
                device = target

                # elegimos la app correcta
            app_name = "android_app" if device.type.lower() == "android" else "ios_app"
            app = get_app(app_name)

            message = messaging.Message(
                data=data or {},
                notification=messaging.Notification(title=title, body=body),
                token=device.registration_id,
            )
            return messaging.send(message, app=app)
        except Exception as e:
            print("Error:: ", str(e))

    @classmethod
    def remove_fcm_device(cls, device_id):
        try:
            device = FCMDevice.objects.filter(device_id=device_id).first()
            if device:
                device.delete()
                print(f"Dispositivo FCM eliminado: {device_id}")
            else:
                print(f"No se encontró un dispositivo con ID: {device_id}")
        except Exception as e:
            print(f"Error al eliminar dispositivo FCM: {str(e)}")


class UserNotificationService:
    @classmethod
    def create_notification(cls, user, title, message):
        from apps.notifications.models import UserNotification

        try:
            UserNotification.objects.create(user=user, title=title, message=message)
        except Exception as e:
            print("Error:: ", str(e))

    @classmethod
    def delete_notification(cls, user, title):
        from apps.notifications.models import UserNotification

        try:
            UserNotification.objects.filter(user=user, title=title).delete()
        except Exception as e:
            print("Error:: ", str(e))
