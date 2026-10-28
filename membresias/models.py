# ============================================================
# membresias/models.py — PLANES, MEMBRESÍAS, PAGOS Y SU HISTORIAL
# Responsabilidad: representar el ciclo de vida de la membresía de
# un socio. La lógica de activación/renovación/congelamiento vive en
# servicios.py; aquí solo van los datos y las restricciones de la
# base de datos que son la última barrera de integridad.
#
# Pago y Membresia.socio NO usan CASCADE (ver adjunto de la pauta):
# un socio no se borra nunca, así que PROTECT es correcto y además
# impide borrar accidentalmente el historial financiero.
# ============================================================

import uuid

from django.db import models
from django.db.models import F, Q
from django.utils import timezone

from socios.models import Socio
from usuarios.models import Usuario


class Plan(models.Model):
    """Plan comercial que un socio puede pagar: precio, duración y límite semanal."""

    nombre = models.CharField("nombre", max_length=100, unique=True)
    descripcion = models.TextField("descripción", blank=True)
    precio = models.PositiveIntegerField("precio (CLP)")
    duracion_dias = models.PositiveIntegerField("duración en días")
    clases_por_semana = models.PositiveIntegerField(
        "clases por semana",
        null=True,
        blank=True,
        help_text="Vacío = sin límite de clases grupales por semana.",
    )
    activo = models.BooleanField("activo", default=True)
    creado_en = models.DateTimeField("creado en", auto_now_add=True)
    actualizado_en = models.DateTimeField("actualizado en", auto_now=True)

    class Meta:
        verbose_name = "plan"
        verbose_name_plural = "planes"
        ordering = ["precio"]
        constraints = [
            models.CheckConstraint(check=Q(precio__gt=0), name="plan_precio_positivo"),
            models.CheckConstraint(check=Q(duracion_dias__gt=0), name="plan_duracion_positiva"),
        ]

    def __str__(self) -> str:
        return f"{self.nombre} (${self.precio:,})".replace(",", ".")


class EstadoMembresia(models.TextChoices):
    ACTIVA = "ACTIVA", "Activa"
    VENCIDA = "VENCIDA", "Vencida"
    CONGELADA = "CONGELADA", "Congelada"


class Membresia(models.Model):
    """Periodo de vigencia de un plan para un socio, con su estado actual."""

    socio = models.ForeignKey(
        Socio, verbose_name="socio", on_delete=models.PROTECT, related_name="membresias"
    )
    plan = models.ForeignKey(
        Plan, verbose_name="plan", on_delete=models.PROTECT, related_name="membresias"
    )
    fecha_inicio = models.DateField("fecha de inicio")
    fecha_fin = models.DateField("fecha de término")
    estado = models.CharField(
        "estado", max_length=12, choices=EstadoMembresia.choices, default=EstadoMembresia.ACTIVA, db_index=True
    )
    dias_congelados = models.PositiveIntegerField("días congelados", default=0)
    fecha_congelamiento = models.DateField("fecha de congelamiento", null=True, blank=True)
    creado_en = models.DateTimeField("creado en", auto_now_add=True)
    actualizado_en = models.DateTimeField("actualizado en", auto_now=True)

    class Meta:
        verbose_name = "membresía"
        verbose_name_plural = "membresías"
        ordering = ["-fecha_inicio"]
        constraints = [
            # Un socio no puede tener, a la vez, más de una membresía ACTIVA o
            # CONGELADA: ambas se consideran "la membresía vigente" del socio.
            models.UniqueConstraint(
                fields=["socio"],
                condition=Q(estado__in=[EstadoMembresia.ACTIVA, EstadoMembresia.CONGELADA]),
                name="una_membresia_activa_o_congelada_por_socio",
            ),
            models.CheckConstraint(check=Q(fecha_fin__gte=F("fecha_inicio")), name="membresia_fechas_coherentes"),
        ]

    def __str__(self) -> str:
        return f"{self.socio} · {self.plan.nombre} ({self.get_estado_display()})"

    @property
    def esta_activa_hoy(self) -> bool:
        """ACTIVA y con fecha_fin aún no alcanzada (no depende de haber corrido el comando)."""
        return self.estado == EstadoMembresia.ACTIVA and self.fecha_fin >= timezone.localdate()


class MetodoPago(models.TextChoices):
    EFECTIVO = "EFECTIVO", "Efectivo"
    DEBITO = "DEBITO", "Débito"
    CREDITO = "CREDITO", "Crédito"
    TRANSFERENCIA = "TRANSFERENCIA", "Transferencia"


def _generar_comprobante() -> str:
    """Código de comprobante único, independiente del id autoincremental."""
    return f"PAGO-{uuid.uuid4().hex[:10].upper()}"


class Pago(models.Model):
    """Pago que activa o renueva una membresía. Registro de auditoría: no se borra."""

    socio = models.ForeignKey(Socio, verbose_name="socio", on_delete=models.PROTECT, related_name="pagos")
    plan = models.ForeignKey(Plan, verbose_name="plan", on_delete=models.PROTECT, related_name="pagos")
    membresia = models.ForeignKey(
        Membresia, verbose_name="membresía", on_delete=models.PROTECT, related_name="pagos"
    )
    monto = models.PositiveIntegerField("monto (CLP)")
    metodo = models.CharField("método de pago", max_length=14, choices=MetodoPago.choices)
    fecha = models.DateTimeField("fecha", auto_now_add=True)
    registrado_por = models.ForeignKey(
        Usuario,
        verbose_name="registrado por",
        on_delete=models.SET_NULL,
        null=True,
        related_name="pagos_registrados",
    )
    comprobante = models.CharField(
        "comprobante", max_length=20, unique=True, default=_generar_comprobante, editable=False
    )

    class Meta:
        verbose_name = "pago"
        verbose_name_plural = "pagos"
        ordering = ["-fecha"]
        constraints = [
            models.CheckConstraint(check=Q(monto__gt=0), name="pago_monto_positivo"),
        ]

    def __str__(self) -> str:
        return f"{self.comprobante} · {self.socio} · ${self.monto:,}".replace(",", ".")


class HistorialEstadoMembresia(models.Model):
    """Auditoría de cada transición de estado de una membresía."""

    membresia = models.ForeignKey(Membresia, on_delete=models.CASCADE, related_name="historial")
    estado_anterior = models.CharField(
        "estado anterior", max_length=12, choices=EstadoMembresia.choices, null=True, blank=True
    )
    estado_nuevo = models.CharField("estado nuevo", max_length=12, choices=EstadoMembresia.choices)
    autor = models.ForeignKey(
        Usuario, verbose_name="autor", on_delete=models.SET_NULL, null=True, related_name="+"
    )
    fecha = models.DateTimeField("fecha", auto_now_add=True)
    observacion = models.CharField("observación", max_length=255, blank=True)

    class Meta:
        verbose_name = "historial de estado de membresía"
        verbose_name_plural = "historial de estados de membresía"
        ordering = ["fecha"]

    def __str__(self) -> str:
        return f"{self.membresia} · {self.estado_anterior} → {self.estado_nuevo}"
