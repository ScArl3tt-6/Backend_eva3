# ============================================================
# accesos/servicios.py — VALIDACIÓN DE ACCESO Y CÁLCULO DEL AFORO
# Responsabilidad: decidir si una ENTRADA o SALIDA se permite, y
# dejar SIEMPRE un registro (permitido o denegado, con su motivo).
#
# Seguridad ante condiciones de carrera: TODO ocurre dentro de una
# sola transaction.atomic() que bloquea, en este orden fijo, la fila
# de Instalacion (el aforo) y luego la del Socio. Como solo existe
# UNA fila de Instalacion, ese bloqueo serializa cualquier par de
# ENTRADAs simultáneas: la segunda petición espera a que la primera
# termine (y su RegistroAcceso ya exista) antes de volver a contar
# la ocupación, así que nunca se supera el aforo ni se duplica una
# entrada sin salida (antipassback).
# ============================================================

import uuid as uuid_lib

from django.db import transaction
from django.db.models import OuterRef, Subquery
from django.utils import timezone

from core.excepciones import ErrorDeNegocio
from membresias.models import EstadoMembresia, Membresia
from membresias.servicios import verificar_vencimiento
from socios.models import Socio

from .models import Instalacion, RegistroAcceso, ResultadoAcceso, TipoAcceso


class TipoAccesoInvalidoError(ErrorDeNegocio):
    mensaje_por_defecto = "El tipo de acceso debe ser ENTRADA o SALIDA."


def _registrar(*, socio, tipo, resultado, motivo, registrado_por, token_crudo="") -> RegistroAcceso:
    return RegistroAcceso.objects.create(
        socio=socio,
        tipo=tipo,
        resultado=resultado,
        motivo=motivo,
        registrado_por=registrado_por,
        token_intentado="" if socio is not None else token_crudo[:64],
    )


def _motivo_membresia(membresia) -> str:
    if membresia is None:
        return "El socio no tiene una membresía registrada."
    if membresia.estado == EstadoMembresia.CONGELADA:
        return "La membresía del socio está congelada."
    if membresia.estado == EstadoMembresia.VENCIDA:
        return "La membresía del socio está vencida."
    return "La membresía del socio no está activa."


def ocupacion_actual() -> int:
    """Cantidad de socios con una ENTRADA permitida sin una SALIDA permitida posterior."""
    ultimo_tipo_permitido = (
        RegistroAcceso.objects.filter(socio=OuterRef("pk"), resultado=ResultadoAcceso.PERMITIDO)
        .order_by("-fecha_hora")
        .values("tipo")[:1]
    )
    return (
        Socio.objects.annotate(ultimo_tipo_permitido=Subquery(ultimo_tipo_permitido))
        .filter(ultimo_tipo_permitido=TipoAcceso.ENTRADA)
        .count()
    )


def _esta_dentro(socio) -> bool:
    """True si el último acceso PERMITIDO del socio fue una ENTRADA (sin salida después)."""
    ultimo = (
        RegistroAcceso.objects.filter(socio=socio, resultado=ResultadoAcceso.PERMITIDO)
        .order_by("-fecha_hora")
        .first()
    )
    return ultimo is not None and ultimo.tipo == TipoAcceso.ENTRADA


@transaction.atomic
def validar_acceso(*, token, tipo: str, registrado_por=None) -> RegistroAcceso:
    """Valida un intento de acceso y SIEMPRE deja un RegistroAcceso, permitido o denegado."""
    if tipo not in TipoAcceso.values:
        raise TipoAccesoInvalidoError()

    # --- Bloqueo en orden fijo: primero la instalación (aforo), luego el socio ---
    instalacion = Instalacion.objects.select_for_update().get(pk=Instalacion.obtener().pk)

    try:
        token_uuid = uuid_lib.UUID(str(token))
    except (ValueError, AttributeError, TypeError):
        token_uuid = None

    socio = None
    if token_uuid is not None:
        socio = Socio.objects.select_for_update().filter(token_qr=token_uuid).first()

    if socio is None:
        return _registrar(
            socio=None, tipo=tipo, resultado=ResultadoAcceso.DENEGADO,
            motivo="El token no corresponde a ningún socio.", registrado_por=registrado_por,
            token_crudo=str(token),
        )

    # --- Membresía vigente en tiempo real (puede marcarla VENCIDA aquí mismo) ---
    ultima_membresia = Membresia.objects.filter(socio=socio).order_by("-fecha_fin").first()
    if ultima_membresia is not None:
        ultima_membresia = verificar_vencimiento(ultima_membresia)

    membresia_activa = (
        ultima_membresia is not None
        and ultima_membresia.estado == EstadoMembresia.ACTIVA
        and ultima_membresia.fecha_fin >= timezone.localdate()
    )

    if not membresia_activa:
        return _registrar(
            socio=socio, tipo=tipo, resultado=ResultadoAcceso.DENEGADO,
            motivo=_motivo_membresia(ultima_membresia), registrado_por=registrado_por,
        )

    dentro = _esta_dentro(socio)

    if tipo == TipoAcceso.ENTRADA:
        if dentro:
            return _registrar(
                socio=socio, tipo=tipo, resultado=ResultadoAcceso.DENEGADO,
                motivo="El socio ya se encuentra dentro (antipassback).", registrado_por=registrado_por,
            )

        if ocupacion_actual() >= instalacion.aforo_maximo:
            return _registrar(
                socio=socio, tipo=tipo, resultado=ResultadoAcceso.DENEGADO,
                motivo="Aforo completo.", registrado_por=registrado_por,
            )

        return _registrar(
            socio=socio, tipo=tipo, resultado=ResultadoAcceso.PERMITIDO, motivo="", registrado_por=registrado_por,
        )

    # --- tipo == SALIDA ---
    if not dentro:
        return _registrar(
            socio=socio, tipo=tipo, resultado=ResultadoAcceso.DENEGADO,
            motivo="No hay una entrada abierta para registrar la salida.", registrado_por=registrado_por,
        )

    return _registrar(
        socio=socio, tipo=tipo, resultado=ResultadoAcceso.PERMITIDO, motivo="", registrado_por=registrado_por,
    )


def cerrar_dia(registrado_por=None) -> int:
    """Registra la SALIDA de quienes quedaron dentro al cierre del día."""
    cerrados = 0
    for socio in Socio.objects.all():
        with transaction.atomic():
            # Se re-bloquea la instalación para mantener el mismo orden de locks
            # que validar_acceso, por si se ejecuta junto con accesos en curso.
            Instalacion.objects.select_for_update().get(pk=Instalacion.obtener().pk)
            socio_bloqueado = Socio.objects.select_for_update().get(pk=socio.pk)
            if _esta_dentro(socio_bloqueado):
                _registrar(
                    socio=socio_bloqueado, tipo=TipoAcceso.SALIDA, resultado=ResultadoAcceso.PERMITIDO,
                    motivo="Salida automática por cierre del día.", registrado_por=registrado_por,
                )
                cerrados += 1
    return cerrados
