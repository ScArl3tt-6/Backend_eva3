# ============================================================
# usuarios/models.py — MODELO DE USUARIO Y ROLES
# Responsabilidad: definir el usuario del sistema con los cuatro
# roles del negocio (ADMINISTRADOR, RECEPCION, INSTRUCTOR, SOCIO),
# sobre la base de AbstractUser para no perder el sistema de
# contraseñas ni los permisos de Django.
#
# Los socios, usuarios y en general las personas NUNCA se borran de
# la base de datos: se desactivan con is_active=False. Así se
# conserva la trazabilidad de sus pagos, accesos y reservas (ver las
# relaciones PROTECT en socios/membresias/accesos/clases).
# ============================================================

from django.contrib.auth.models import AbstractUser
from django.db import models


class Rol(models.TextChoices):
    """Roles del negocio: qué puede hacer cada persona en FitLife."""

    ADMINISTRADOR = "ADMINISTRADOR", "Administrador"
    RECEPCION = "RECEPCION", "Recepción"
    INSTRUCTOR = "INSTRUCTOR", "Instructor"
    SOCIO = "SOCIO", "Socio"


class Usuario(AbstractUser):
    """Usuario del sistema; su rol define qué puede hacer en la web y en la API."""

    email = models.EmailField(
        "correo electrónico",
        unique=True,
        help_text="Debe ser único; se usa para identificar a la persona.",
    )
    rol = models.CharField(
        "rol",
        max_length=20,
        choices=Rol.choices,
        default=Rol.SOCIO,
        db_index=True,
        help_text="Define los permisos del usuario en la web y en la API.",
    )
    telefono = models.CharField("teléfono", max_length=20, blank=True)
    creado_en = models.DateTimeField("creado en", auto_now_add=True)
    actualizado_en = models.DateTimeField("actualizado en", auto_now=True)

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
        ordering = ["username"]
        indexes = [
            models.Index(fields=["rol"], name="usuario_rol_idx"),
            models.Index(fields=["is_active"], name="usuario_activo_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.username} ({self.get_rol_display()})"

    # ============================================================
    # SINCRONIZACIÓN DE rol CON is_staff
    # Solo el rol ADMINISTRADOR entra al Django Admin. El campo rol
    # sigue siendo la única fuente de verdad: is_staff se recalcula
    # en cada guardado para que nunca queden desincronizados.
    # ============================================================
    def save(self, *args, **kwargs):
        self.is_staff = self.rol == Rol.ADMINISTRADOR
        super().save(*args, **kwargs)

    @property
    def es_administrador(self) -> bool:
        return self.rol == Rol.ADMINISTRADOR

    @property
    def es_recepcion(self) -> bool:
        return self.rol == Rol.RECEPCION

    @property
    def es_instructor(self) -> bool:
        return self.rol == Rol.INSTRUCTOR

    @property
    def es_socio(self) -> bool:
        return self.rol == Rol.SOCIO

    @property
    def nombre_completo(self) -> str:
        completo = f"{self.first_name} {self.last_name}".strip()
        return completo or self.username
