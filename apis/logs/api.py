from rest_framework import viewsets, permissions
from auditlog.models import LogEntry
from apis.logs.serialize import LogEntrySerializer


class LogEntryViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = LogEntry.objects.all().order_by('-timestamp')
    serializer_class = LogEntrySerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(actor=self.request.user)

    def perform_update(self, serializer):
        print(self.request.user)
        serializer.save(actor=self.request.user)

    def get_queryset(self):
        """
        Permite filtrar logs por usuario si se proporciona un parámetro ?user=username.
        """
        queryset = super().get_queryset()
        user = self.request.query_params.get('user', None)

        if user:
            queryset = queryset.filter(actor__username=user)

        return queryset



