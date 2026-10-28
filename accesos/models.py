# ============================================================
# accesos/models.py — AFORO DE LA INSTALACIÓN Y REGISTRO DE ACCESOS
# Instalacion es una tabla "singleton" (una sola fila, creada por
# migración de datos y reforzada por seed_data): el aforo máximo
# vive en la base de datos —no en el .env— precisamente para poder
# bloquear esa fila con select_for_update() en accesos/servicios.py
# y evitar condiciones de carrera al validar el acceso.
# ============================================================

from django.db import models
from django.db.models import Q

from socios.models import Socio
from usuarios.models import Usuario


class Instalacion(models.Model):
    """Datos del gimnasio relevantes para el control de aforo. Una sola fila."""

    nombre = models.CharField("nombre", max_length=100, default="FitLife")
    aforo_maximo = models.PositiveIntegerField("aforo máximo")
    actualizado_en = models.DateTimeField("actualizado en", auto_now=True)

    class Meta:
        verbose_name = "instalación"
        verbose_name_plural = "instalación (aforo)"
        constraints = [
            models.CheckConstraint(check=Q(aforo_maximo__gt=0), name="instalacion_aforo_positivo"),
        ]

    def __str__(self) -> str:
        return f"{self.nombre} (aforo máximo: {self.aforo_maximo})"

    @classmethod
    def obtener(cls) -> "Instalacion":
        """Devuelve la única fila de instalación; la crea si por algún motivo falta."""
        instalacion = cls.objects.first()
        if instalacion is None:
            instalacion = cls.objects.create(nombre="FitLife", aforo_maximo=50)
        return instalacion


class TipoAcceso(models.TextChoices):
    ENTRADA = "ENTRADA", "Entrada"
    SALIDA = "SALIDA", "Salida"


class ResultadoAcceso(models.TextChoices):
    PERMITIDO = "PERMITIDO", "Permitido"
    DENEGADO = "DENEGADO", "Denegado"


class RegistroAcceso(models.Model):
    """Cada intento de acceso, permitido o denegado. Nunca se edita ni se borra."""

    socio = models.ForeignKey(
        Socio,
        verbose_name="socio",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="accesos",
        help_text="Vacío cuando el token escaneado no corresponde a ningún socio.",
    )
    token_intentado = models.CharField(
        "token intentado",
        max_length=64,
        blank=True,
        help_text="Solo se guarda cuando el token no corresponde a ningún socio (auditoría).",
    )
    tipo = models.CharField("tipo", max_length=10, choices=TipoAcceso.choices)
    fecha_hora = models.DateTimeField("fecha y hora", auto_now_add=True)
    resultado = models.CharField("resultado", max_length=10, choices=ResultadoAcceso.choices, db_index=True)
    motivo = models.CharField("motivo", max_length=255, blank=True)
    registrado_por = models.ForeignKey(
        Usuario,
        verbose_name="registrado por",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="accesos_registrados",
    )

    class Meta:
        verbose_name = "registro de acceso"
        verbose_name_plural = "registros de acceso"
        ordering = ["-fecha_hora"]
        indexes = [
            models.Index(fields=["socio", "resultado", "fecha_hora"], name="acceso_socio_resultado_idx"),
        ]

    def __str__(self) -> str:
        quien = str(self.socio) if self.socio else "token desconocido"
        return f"{quien} · {self.tipo} · {self.resultado}"
