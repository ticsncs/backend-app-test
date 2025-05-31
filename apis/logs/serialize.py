from rest_framework import serializers
from auditlog.models import LogEntry

class LogEntrySerializer(serializers.ModelSerializer):
    action = serializers.SerializerMethodField()
    timestamp = serializers.DateTimeField(format="%d-%m-%Y %H:%M:%S")
    actor = serializers.SerializerMethodField()

    class Meta:
        model = LogEntry
        fields = ['id', 'timestamp', 'actor', 'action', 'object_repr', 'changes', 'remote_addr']

    def get_action(self, obj):
        return dict(LogEntry.Action.choices).get(obj.action, "Desconocido")

    def get_actor(self, obj):
        return obj.actor.username if obj.actor else "Sistema"
