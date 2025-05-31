from django.apps import AppConfig


class ClientsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.clients"
    verbose_name = "Clientes"

    def ready(self):
        try:
            import apps.clients.signals
        except ImportError as e:
            raise ImportError(f"Error al importar señales: {e}")