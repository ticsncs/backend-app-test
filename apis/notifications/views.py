from django.shortcuts import get_object_or_404
from fcm_django.api.rest_framework import FCMDeviceSerializer
from fcm_django.models import FCMDevice
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from apps.notifications.services import FirebaseNotificationService
from apis.notifications.serializers import NotificationTemplateSerializer
from apps.clients.models import UserProfile
from apps.notifications.models import UserNotification, NotificationTemplate


class CustomDeviceCreateView(APIView):
    permission_classes = [AllowAny]
    """
    Custom view to create a device and associate it with a user.
    """

    def get(self, request, format=None):
        user_id = request.query_params.get('user_id')
        registration_id = request.query_params.get('registration_id', None)
        user = UserProfile.objects.filter(pk=user_id).first()
        if user:
            # fcm_devices = FCMDevice.objects.filter(user=user)
            # fcm_serialized = FCMDeviceSerializer(fcm_devices, many=True).data
            # return Response({"fcm_devices": fcm_serialized},
            #                 status=status.HTTP_200_OK)
            fcm = FCMDevice.objects.filter(user=user,
                                           registration_id=registration_id).first()
            if fcm:
                fcm_serialized = FCMDeviceSerializer(fcm).data
                return Response({"fcm": fcm_serialized},
                                status=status.HTTP_201_CREATED)
            return Response({"error": "FCM Device not found"},
                            status=status.HTTP_204_NO_CONTENT)
        return Response({"error": "User not found"},
                        status=status.HTTP_204_NO_CONTENT)

    def post(self, request, *args, **kwargs):
        user_id = request.data.get('user_id')
        name = request.data.get('name')
        user = UserProfile.objects.filter(pk=user_id).first()
        if not user:
            return Response({"error": "user not found, user are required"},
                            status=status.HTTP_400_BAD_REQUEST)
        registration_id = request.data.get('registration_id')
        device_id = request.data.get('device_id')
        device_type = request.data.get('type')

        if not registration_id or not device_type:
            return Response({"error": "registration_id and type are required"},
                            status=status.HTTP_400_BAD_REQUEST)

        device, created = FCMDevice.objects.get_or_create(
            registration_id=registration_id,
            defaults={"user": user, "type": device_type, "name": name,
                      "device_id": device_id, }
        )

        if device:
            device.type = device_type
            device.device_id = device_id
            device.save()

        return Response({"detail": "Device registered successfully."},
                        status=status.HTTP_201_CREATED)

    def put(self, request, *args, **kwargs):

        registration_id = request.data.get('registration_id')
        user = request.data.get('user_id')
        if not registration_id:
            return Response(
                {"error": "El campo registration_id  es obligatorio"},
                status=status.HTTP_400_BAD_REQUEST)
        if not user:
            return Response({"error": "El campo user  es obligatorio"},
                            status=status.HTTP_400_BAD_REQUEST)
        device_id = request.data.get('device_id')
        device_type = request.data.get('type')
        name = request.data.get('name')
        device, updated = FCMDevice.objects.update_or_create(
            registration_id=registration_id,
            defaults={"user": user, "type": device_type, "name": name,
                      "device_id": device_id, }
        )
        # old_fcm_device = FCMDevice.objects.filter(
        #     user=user,registration_id=registration_id
        # ).first()
        #
        # old_fcm_device.registration_id = registration_id
        # old_fcm_device.save()
        return Response({"detail": "Device updated successfully."},
                        status=status.HTTP_201_CREATED)


class UserNotificationsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id=None):
        print(user_id, "asdasdasdasdadasd")
        if user_id:
            user = get_object_or_404(UserProfile, id=user_id)
            notifications = user.notifications.all()
            unread_count = notifications.filter(is_read=False).count()
            return Response({
                "user_id": user.id,
                "total_notifications": notifications.count(),
                "unread_count": unread_count,
                "notifications": [
                    {
                        "id": n.id,
                        "title": n.title,
                        "message": n.message,
                        "is_read": n.is_read,
                        "created_at": n.created_at,
                        "read_at": n.read_at,
                    }
                    for n in notifications
                ]
            }, status=status.HTTP_200_OK)


class NotificationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        UserNotification.objects.filter(user_id=user_id, is_read=False).update(
            is_read=True)

        return Response({
            "message": "all notifications marked as read",

        }, status=status.HTTP_200_OK)


class FirebaseNotificationView(ModelViewSet):
    """
    Api para generar notificaicones masivas de firebase
    """
    serializer_class = NotificationTemplateSerializer
    queryset = NotificationTemplate.objects.all()
    http_method_names = ['post']

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        device_id = request.data.get("device_id")
        if not device_id:
            return Response({"error": "device_id es requerido."}, status=status.HTTP_400_BAD_REQUEST)

        device = get_object_or_404(FCMDevice, device_id=device_id)

        # Eliminar solo el dispositivo FCM específico
        device.delete()

        # Si usas tokens, elimínalos aquí
        if hasattr(request, "auth") and request.auth:
            request.auth.delete()

        return Response({"message": f"Dispositivo {device_id} eliminado correctamente."}, status=status.HTTP_200_OK)
