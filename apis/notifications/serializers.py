from django.utils.timezone import localtime, make_aware
from rest_framework import serializers

from apps.notifications.models import NotificationTemplate


class NotificationTemplateSerializer(serializers.ModelSerializer):
    title = serializers.CharField(required=True)
    body = serializers.CharField(required=True)
    send_at = serializers.DateField(required=True)

    class Meta:
        model = NotificationTemplate
        fields = ["title", "body", "send_at"]

    def validate_send_at(self, value):
        from django.utils.timezone import now
        current_time = localtime(now())
        if value < current_time.date():
            raise serializers.ValidationError(
                "La fecha de envío, no debe ser menor  a la fecha actual.")
        return value

    def validate_title(self, value):
        if len(value) < 5:
            raise serializers.ValidationError(
                "El título debe tener al menos 5 caracteres.")
        return value

    def validate_body(self, value):
        if not value.strip() or len(
                value.strip()) < 5:  # Verifica si el campo está vacío o tiene solo espacios
            raise serializers.ValidationError(
                "El cuerpo del mensaje no puede estar vacío. ó tener menos de 5 caracteres")
        return value
