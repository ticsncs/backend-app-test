from django.core.management.base import BaseCommand
from apps.clients.services import assign_anniversary_points


class Command(BaseCommand):
    help = "Asigna puntos de aniversario"

    def handle(self, *args, **kwargs):
        assign_anniversary_points()
        self.stdout.write(
            self.style.SUCCESS("✅ Puntos de aniversario asignados correctamente")
        )
