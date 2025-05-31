from django.core.management.base import BaseCommand
from apps.clients.services import assign_christmas_points


class Command(BaseCommand):
    help = "Asigna puntos de navidad"

    def handle(self, *args, **kwargs):
        assign_christmas_points()
        self.stdout.write(
            self.style.SUCCESS("✅ Puntos de navidad asignados correctamente")
        )
