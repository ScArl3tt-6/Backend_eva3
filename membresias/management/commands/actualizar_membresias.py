# ============================================================
# membresias/management/commands/actualizar_membresias.py
# Marca VENCIDA toda membresía ACTIVA cuya fecha_fin ya pasó.
# Idempotente: ejecutarlo varias veces el mismo día no vuelve a
# procesar las que ya quedaron VENCIDA (el filtro solo toma ACTIVA).
# Pensado para correr una vez al día (cron / systemd timer en el
# servidor), aunque también se verifica en tiempo real al validar
# un acceso o crear una reserva.
# ============================================================
from django.core.management.base import BaseCommand

from membresias.servicios import actualizar_membresias_vencidas


class Command(BaseCommand):
    help = "Marca como VENCIDA toda membresía ACTIVA cuya fecha de término ya pasó."

    def handle(self, *args, **options):
        total = actualizar_membresias_vencidas()
        self.stdout.write(self.style.SUCCESS(f"Membresías actualizadas a VENCIDA: {total}"))
