from rest_framework import serializers

from apps.appsettings.models import DynamicContent


class DynamicContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = DynamicContent
        fields = ['key', 'content_type', 'text', 'image', 'updated_at']
