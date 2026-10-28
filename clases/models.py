# ============================================================
# clases/models.py — TIPOS DE CLASE, CLASES Y RESERVAS
# Responsabilidad: datos de las clases grupales y sus reservas. La
# lógica de cupos, lista de espera y cancelaciones vive en
# servicios.py; aquí solo van los datos y las restricciones que son
# la última barrera de integridad.
#
# Reserva.socio usa PROTECT (no CASCADE): un socio no se borra
# nunca, y una reserva es parte de su historial de asistencia.
# ============================================================

from django.db import models
from django.db.models import F, Q

from socios.models import Socio
from usuarios.models import Rol, Usuario


class TipoClase(models.Model):
    """Categoría de clase grupal (Spinning, Yoga, Funcional, etc.)."""

    nombre = models.CharField("nombre", max_length=100, unique=True)
    descripcion = models.TextField("descripción", blank=True)

    class Meta:
        verbose_name = "tipo de clase"
        verbose_name_plural = "tipos de clase"
        ordering = ["nombre"]

    def __str__(self) -> str:
        return self.nombre


class EstadoClase(models.TextChoices):
    PROGRAMADA = "PROGRAMADA", "Programada"
    EN_CURSO = "EN_CURSO", "En curso"
    FINALIZADA = "FINALIZADA", "Finalizada"
    CANCELADA = "CANCELADA", "Cancelada"


class Clase(models.Model):
    """Sesión concreta de un tipo de clase, con cupo, horario e instructor."""

    tipo = models.ForeignKey(TipoClase, verbose_name="tipo de clase", on_delete=models.PROTECT, related_name="clases")
    instructor = models.ForeignKey(
        Usuario,
        verbose_name="instructor",
        on_delete=models.PROTECT,
        related_name="clases_a_cargo",
        limit_choices_to={"rol": Rol.INSTRUCTOR},
    )
    sala = models.CharField("sala", max_length=50)
    inicio = models.DateTimeField("inicio")
    fin = models.DateTimeField("término")
    cupo_maximo = models.PositiveIntegerField("cupo máximo")
    estado = models.CharField(
        "estado", max_length=12, choices=EstadoClase.choices, default=EstadoClase.PROGRAMADA, db_index=True
    )
    creado_en = models.DateTimeField("creado en", auto_now_add=True)
    actualizado_en = models.DateTimeField("actualizado en", auto_now=True)

    class Meta:
        verbose_name = "clase"
        verbose_name_plural = "clases"
        ordering = ["inicio"]
        constraints = [
            models.CheckConstraint(check=Q(cupo_maximo__gt=0), name="clase_cupo_positivo"),
            models.CheckConstraint(check=Q(fin__gt=F("inicio")), name="clase_fin_posterior_a_inicio"),
        ]

    def __str__(self) -> str:
        return f"{self.tipo} · {self.inicio:%d-%m-%Y %H:%M}"

    @property
    def cupos_confirmados(self) -> int:
        return self.reservas.filter(estado=EstadoReserva.CONFIRMADA).count()

    @property
    def en_lista_de_espera(self) -> int:
        return self.reservas.filter(estado=EstadoReserva.EN_ESPERA).count()


class EstadoReserva(models.TextChoices):
    CONFIRMADA = "CONFIRMADA", "Confirmada"
    EN_ESPERA = "EN_ESPERA", "En espera"
    CANCELADA = "CANCELADA", "Cancelada"
    ASISTIO = "ASISTIO", "Asistió"
    NO_ASISTIO = "NO_ASISTIO", "No asistió"


class Reserva(models.Model):
    """Cupo de un socio en una clase: confirmado, en espera o su desenlace."""

    clase = models.ForeignKey(Clase, verbose_name="clase", on_delete=models.CASCADE, related_name="reservas")
    socio = models.ForeignKey(Socio, verbose_name="socio", on_delete=models.PROTECT, related_name="reservas")
    estado = models.CharField("estado", max_length=12, choices=EstadoReserva.choices, db_index=True)
    posicion_espera = models.PositiveIntegerField("posición en la lista de espera", null=True, blank=True)
    creada_en = models.DateTimeField("creada en", auto_now_add=True)
    actualizada_en = models.DateTimeField("actualizada en", auto_now=True)

    class Meta:
        verbose_name = "reserva"
        verbose_name_plural = "reservas"
        ordering = ["clase", "posicion_espera", "creada_en"]
        constraints = [
            # Una sola reserva activa (confirmada o en espera) por socio y clase.
            models.UniqueConstraint(
                fields=["clase", "socio"],
                condition=Q(estado__in=[EstadoReserva.CONFIRMADA, EstadoReserva.EN_ESPERA]),
                name="una_reserva_activa_por_socio_y_clase",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.socio} · {self.clase} · {self.get_estado_display()}"
