# ============================================================
# clases/servicios.py — RESERVAS, CUPOS, LISTA DE ESPERA Y ASISTENCIA
# Responsabilidad: toda la lógica de negocio de las clases grupales.
#
# Seguridad ante sobrecupo: reservar_clase() y cancelar_reserva()
# bloquean primero la fila de la Clase con select_for_update(): dos
# reservas simultáneas para el último cupo se serializan, así que
# nunca queda más gente CONFIRMADA que cupo_maximo.
# ============================================================

from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import F, Max
from django.utils import timezone

from core.excepciones import ErrorDeNegocio
from membresias.models import EstadoMembresia, Membresia
from membresias.servicios import verificar_vencimiento

from .models import Clase, EstadoClase, EstadoReserva, Reserva


class MembresiaNoActivaError(ErrorDeNegocio):
    mensaje_por_defecto = "El socio no tiene una membresía activa y vigente para la fecha de la clase."


class ClaseNoDisponibleError(ErrorDeNegocio):
    mensaje_por_defecto = "La clase no está disponible para reservar."


class ReservaDuplicadaError(ErrorDeNegocio):
    mensaje_por_defecto = "El socio ya tiene una reserva activa en esta clase."


class LimiteSemanalError(ErrorDeNegocio):
    mensaje_por_defecto = "El socio ya alcanzó el límite semanal de clases de su plan."


class CancelacionFueraDePlazoError(ErrorDeNegocio):
    mensaje_por_defecto = "Ya no se puede cancelar: pasó el plazo mínimo antes del inicio de la clase."


class TransicionInvalidaError(ErrorDeNegocio):
    mensaje_por_defecto = "Esa acción no está permitida en el estado actual."


def _inicio_de_semana(fecha):
    """Lunes de la semana de "fecha" (weekday(): lunes=0 ... domingo=6)."""
    return fecha - timedelta(days=fecha.weekday())


def _reservas_confirmadas_en_semana(socio, fecha_clase) -> int:
    inicio_semana = _inicio_de_semana(fecha_clase)
    fin_semana = inicio_semana + timedelta(days=6)
    return Reserva.objects.filter(
        socio=socio,
        estado=EstadoReserva.CONFIRMADA,
        clase__inicio__date__gte=inicio_semana,
        clase__inicio__date__lte=fin_semana,
    ).count()


def _membresia_valida_para_la_clase(socio, fecha_clase):
    """Devuelve la última membresía del socio si cubre HOY y la fecha de la clase; si no, None."""
    ultima_membresia = Membresia.objects.filter(socio=socio).order_by("-fecha_fin").first()
    if ultima_membresia is None:
        return None

    ultima_membresia = verificar_vencimiento(ultima_membresia)
    hoy = timezone.localdate()

    if (
        ultima_membresia.estado == EstadoMembresia.ACTIVA
        and ultima_membresia.fecha_fin >= hoy
        and ultima_membresia.fecha_fin >= fecha_clase
    ):
        return ultima_membresia
    return None


# ============================================================
# BLOQUE 1 — RESERVAR
# ============================================================
@transaction.atomic
def reservar_clase(socio, clase: Clase) -> Reserva:
    """Reserva un cupo en la clase: CONFIRMADA si hay espacio, EN_ESPERA si no."""
    clase = Clase.objects.select_for_update().get(pk=clase.pk)

    if clase.estado in (EstadoClase.CANCELADA, EstadoClase.FINALIZADA):
        raise ClaseNoDisponibleError(
            f"La clase está {clase.get_estado_display().lower()}: no se puede reservar."
        )

    if clase.inicio <= timezone.now():
        raise ClaseNoDisponibleError("No se puede reservar una clase que ya comenzó o ya terminó.")

    membresia = _membresia_valida_para_la_clase(socio, clase.inicio.date())
    if membresia is None:
        raise MembresiaNoActivaError()

    ya_reservada = Reserva.objects.filter(
        clase=clase, socio=socio, estado__in=[EstadoReserva.CONFIRMADA, EstadoReserva.EN_ESPERA]
    ).exists()
    if ya_reservada:
        raise ReservaDuplicadaError()

    if membresia.plan.clases_por_semana is not None:
        confirmadas_semana = _reservas_confirmadas_en_semana(socio, clase.inicio.date())
        if confirmadas_semana >= membresia.plan.clases_por_semana:
            raise LimiteSemanalError(
                f"El plan «{membresia.plan.nombre}» permite {membresia.plan.clases_por_semana} "
                "clase(s) por semana y ya fueron reservadas."
            )

    confirmadas_actuales = Reserva.objects.filter(clase=clase, estado=EstadoReserva.CONFIRMADA).count()

    if confirmadas_actuales < clase.cupo_maximo:
        return Reserva.objects.create(clase=clase, socio=socio, estado=EstadoReserva.CONFIRMADA)

    ultima_posicion = (
        Reserva.objects.filter(clase=clase, estado=EstadoReserva.EN_ESPERA).aggregate(m=Max("posicion_espera"))["m"]
        or 0
    )
    return Reserva.objects.create(
        clase=clase, socio=socio, estado=EstadoReserva.EN_ESPERA, posicion_espera=ultima_posicion + 1
    )


# ============================================================
# BLOQUE 2 — CANCELAR (PROMUEVE AL PRIMERO DE LA LISTA DE ESPERA)
# ============================================================
@transaction.atomic
def cancelar_reserva(reserva: Reserva, autor=None) -> Reserva:
    """Cancela la reserva; si era CONFIRMADA, promueve al primero en espera."""
    clase = Clase.objects.select_for_update().get(pk=reserva.clase_id)
    reserva = Reserva.objects.select_for_update().get(pk=reserva.pk)

    if reserva.estado not in (EstadoReserva.CONFIRMADA, EstadoReserva.EN_ESPERA):
        raise TransicionInvalidaError(
            f"La reserva está {reserva.get_estado_display().lower()}: ya no se puede cancelar."
        )

    limite = timedelta(minutes=settings.CANCELACION_MINUTOS_LIMITE)
    if clase.inicio - timezone.now() < limite:
        raise CancelacionFueraDePlazoError(
            f"Solo se puede cancelar hasta {settings.CANCELACION_MINUTOS_LIMITE} minutos antes del inicio."
        )

    estado_anterior = reserva.estado
    posicion_vacante = reserva.posicion_espera if estado_anterior == EstadoReserva.EN_ESPERA else None

    reserva.estado = EstadoReserva.CANCELADA
    reserva.posicion_espera = None
    reserva.save(update_fields=["estado", "posicion_espera", "actualizada_en"])

    if estado_anterior == EstadoReserva.CONFIRMADA:
        primero_en_espera = (
            Reserva.objects.select_for_update()
            .filter(clase=clase, estado=EstadoReserva.EN_ESPERA)
            .order_by("posicion_espera")
            .first()
        )
        if primero_en_espera is not None:
            posicion_vacante = primero_en_espera.posicion_espera
            primero_en_espera.estado = EstadoReserva.CONFIRMADA
            primero_en_espera.posicion_espera = None
            primero_en_espera.save(update_fields=["estado", "posicion_espera", "actualizada_en"])

    if posicion_vacante is not None:
        Reserva.objects.filter(
            clase=clase, estado=EstadoReserva.EN_ESPERA, posicion_espera__gt=posicion_vacante
        ).update(posicion_espera=F("posicion_espera") - 1)

    return reserva


# ============================================================
# BLOQUE 3 — CANCELAR LA CLASE COMPLETA
# ============================================================
@transaction.atomic
def cancelar_clase(clase: Clase, autor=None) -> Clase:
    """Cancela la clase y, en la misma transacción, cancela todas sus reservas activas."""
    clase = Clase.objects.select_for_update().get(pk=clase.pk)
    clase.estado = EstadoClase.CANCELADA
    clase.save(update_fields=["estado", "actualizado_en"])

    Reserva.objects.filter(clase=clase, estado__in=[EstadoReserva.CONFIRMADA, EstadoReserva.EN_ESPERA]).update(
        estado=EstadoReserva.CANCELADA, posicion_espera=None
    )
    return clase


# ============================================================
# BLOQUE 4 — ASISTENCIA (SOLO TRAS INICIADA LA CLASE)
# ============================================================
@transaction.atomic
def marcar_asistencia(reserva: Reserva, asistio: bool) -> Reserva:
    """Marca ASISTIO/NO_ASISTIO; solo procede si la clase ya comenzó."""
    clase = reserva.clase
    if timezone.now() < clase.inicio:
        raise TransicionInvalidaError("No se puede marcar asistencia antes de que la clase haya comenzado.")

    reserva = Reserva.objects.select_for_update().get(pk=reserva.pk)
    if reserva.estado != EstadoReserva.CONFIRMADA:
        raise TransicionInvalidaError(
            f"Solo se puede marcar asistencia a una reserva CONFIRMADA (estado actual: {reserva.get_estado_display()})."
        )

    reserva.estado = EstadoReserva.ASISTIO if asistio else EstadoReserva.NO_ASISTIO
    reserva.save(update_fields=["estado", "actualizada_en"])
    return reserva
