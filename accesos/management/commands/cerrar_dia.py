# ============================================================
# accesos/management/commands/cerrar_dia.py
# Registra la SALIDA de todos los socios que quedaron con una
# ENTRADA abierta, al cierre de la jornada (se corre una vez al día,
# por ejemplo con un cron/systemd timer en el servidor).
# ============================================================
from django.core.management.base import BaseCommand

from accesos.servicios import cerrar_dia


class Command(BaseCommand):
    help = "Registra la salida automática de los socios que quedaron dentro al cierre del día."

    def handle(self, *args, **options):
        total = cerrar_dia()
        self.stdout.write(self.style.SUCCESS(f"Salidas automáticas registradas: {total}"))
