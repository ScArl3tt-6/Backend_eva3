# ============================================================
# socios/models.py — PERFIL DEL SOCIO
# Responsabilidad: datos propios de un socio (identidad legal,
# contacto de emergencia y token QR). El socio NUNCA se borra de la
# base de datos: su cuenta de usuario se desactiva (is_active=False),
# por eso Socio.usuario usa on_delete=PROTECT y no CASCADE.
# ============================================================

import uuid

from django.db import models

from usuarios.models import Rol, Usuario

from .validadores import formatear_rut, validar_rut


class Socio(models.Model):
    """Perfil de un usuario con rol SOCIO: RUT, contacto y QR de acceso."""

    usuario = models.OneToOneField(
        Usuario,
        verbose_name="usuario",
        on_delete=models.PROTECT,
        related_name="socio",
        limit_choices_to={"rol": Rol.SOCIO},
        help_text="Cuenta de acceso del socio. Las personas no se borran: se desactivan.",
    )
    rut = models.CharField(
        "RUT",
        max_length=12,
        unique=True,
        validators=[validar_rut],
        help_text="Se guarda normalizado como 12345678-5, sin puntos.",
    )
    telefono = models.CharField("teléfono", max_length=20, blank=True)
    contacto_emergencia_nombre = models.CharField("contacto de emergencia", max_length=150, blank=True)
    contacto_emergencia_telefono = models.CharField("teléfono de emergencia", max_length=20, blank=True)
    token_qr = models.UUIDField(
        "token QR",
        default=uuid.uuid4,
        unique=True,
        editable=False,
        help_text="Identifica al socio en el control de acceso. No contiene datos personales.",
    )
    creado_en = models.DateTimeField("creado en", auto_now_add=True)
    actualizado_en = models.DateTimeField("actualizado en", auto_now=True)

    class Meta:
        verbose_name = "socio"
        verbose_name_plural = "socios"
        ordering = ["usuario__username"]

    def __str__(self) -> str:
        return f"{self.usuario.nombre_completo} ({self.rut})"

    def save(self, *args, **kwargs):
        """Normaliza el RUT antes de guardar, para que la unicidad sea confiable."""
        if self.rut:
            self.rut = formatear_rut(self.rut)
        super().save(*args, **kwargs)

    def regenerar_token_qr(self) -> None:
        """Asigna un token nuevo; el anterior deja de servir de inmediato."""
        self.token_qr = uuid.uuid4()
        self.save(update_fields=["token_qr", "actualizado_en"])
