from django.core.management.base import BaseCommand
from apps.clients.services import assign_birthday_points


class Command(BaseCommand):
    help = "Asigna puntos de cumpleaños"

    def handle(self, *args, **kwargs):
        assign_birthday_points()
        self.stdout.write(
            self.style.SUCCESS("✅ Puntos de cumpleaños asignados correctamente")
        )
