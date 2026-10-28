# ============================================================
# membresias/servicios.py — ACTIVACIÓN, RENOVACIÓN Y ESTADOS
# Responsabilidad: toda la lógica de negocio de membresías y pagos.
# Las vistas (web y API) solo llaman a estas funciones; nunca tocan
# los modelos directamente para estos flujos.
#
# registrar_pago() cubre los tres casos exigidos:
#   1) Membresía CONGELADA  → rechaza el pago (debe descongelarse antes).
#   2) Membresía ACTIVA vigente → extiende fecha_fin desde esa fecha.
#   3) Sin membresía vigente (ninguna, o quedó VENCIDA recién) → crea una
#      nueva desde hoy.
# Siempre se bloquea la membresía vigente del socio con select_for_update()
# ANTES de decidir, para que dos pagos simultáneos no renueven dos veces.
# ============================================================

from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from core.excepciones import ErrorDeNegocio

from .models import EstadoMembresia, HistorialEstadoMembresia, Membresia, Pago


class MontoInvalidoError(ErrorDeNegocio):
    """El monto pagado no coincide con el precio del plan."""

    mensaje_por_defecto = "El monto pagado no coincide con el precio del plan."


class MembresiaCongeladaError(ErrorDeNegocio):
    """No se puede pagar/renovar mientras la membresía esté congelada."""

    mensaje_por_defecto = "El socio tiene una membresía congelada: descongele la membresía antes de renovar."


class TransicionInvalidaError(ErrorDeNegocio):
    """Congelar/descongelar desde un estado que no lo permite."""

    mensaje_por_defecto = "La transición de estado solicitada no está permitida."


class RangoDeCongelamientoError(ErrorDeNegocio):
    """Los días de congelamiento solicitados están fuera del rango configurado."""

    mensaje_por_defecto = "La cantidad de días a congelar está fuera del rango permitido."


# ============================================================
# BLOQUE 1 — MÁQUINA DE ESTADOS
# VENCIDA solo se alcanza automáticamente, por fecha, desde ACTIVA.
# Una membresía CONGELADA no vence mientras esté congelada: el
# tiempo congelado no corre en su contra.
# ============================================================
TRANSICIONES_PERMITIDAS: dict[str, set[str]] = {
    EstadoMembresia.ACTIVA: {EstadoMembresia.VENCIDA, EstadoMembresia.CONGELADA},
    EstadoMembresia.CONGELADA: {EstadoMembresia.ACTIVA},
    EstadoMembresia.VENCIDA: {EstadoMembresia.ACTIVA},
}


def _registrar_historial(membresia, anterior, nuevo, autor=None, observacion=""):
    """Anota una transición de estado en el historial de la membresía."""
    return HistorialEstadoMembresia.objects.create(
        membresia=membresia,
        estado_anterior=anterior,
        estado_nuevo=nuevo,
        autor=autor if (autor is not None and getattr(autor, "is_authenticated", True)) else None,
        observacion=observacion[:255],
    )


# ============================================================
# BLOQUE 2 — VENCIMIENTO EN TIEMPO REAL (IDEMPOTENTE)
# La llaman el comando "actualizar_membresias", registrar_pago() y
# accesos/clases antes de confiar en el estado guardado: el estado
# en la base puede estar un día atrasado si nadie corrió el comando.
# ============================================================
def verificar_vencimiento(membresia: Membresia) -> Membresia:
    """Si está ACTIVA y su fecha_fin ya pasó, la marca VENCIDA. No hace nada si no corresponde."""
    hoy = timezone.localdate()
    if membresia.estado == EstadoMembresia.ACTIVA and membresia.fecha_fin < hoy:
        anterior = membresia.estado
        membresia.estado = EstadoMembresia.VENCIDA
        membresia.save(update_fields=["estado", "actualizado_en"])
        _registrar_historial(
            membresia, anterior, EstadoMembresia.VENCIDA, observacion="Vencida automáticamente por fecha."
        )
    return membresia


def actualizar_membresias_vencidas(autor=None) -> int:
    """Recorre todas las membresías ACTIVA vencidas por fecha y las marca VENCIDA. Idempotente."""
    hoy = timezone.localdate()
    actualizadas = 0
    with transaction.atomic():
        vencidas = list(
            Membresia.objects.select_for_update().filter(estado=EstadoMembresia.ACTIVA, fecha_fin__lt=hoy)
        )
        for membresia in vencidas:
            membresia.estado = EstadoMembresia.VENCIDA
            membresia.save(update_fields=["estado", "actualizado_en"])
            _registrar_historial(
                membresia,
                EstadoMembresia.ACTIVA,
                EstadoMembresia.VENCIDA,
                autor=autor,
                observacion="Vencida automáticamente por fecha (comando actualizar_membresias).",
            )
            actualizadas += 1
    return actualizadas


# ============================================================
# BLOQUE 3 — PAGO: ACTIVA O RENUEVA LA MEMBRESÍA
# ============================================================
@transaction.atomic
def registrar_pago(*, socio, plan, monto: int, metodo: str, registrado_por=None) -> Pago:
    """Registra el pago y activa/renueva la membresía del socio en una sola transacción."""
    if monto != plan.precio:
        raise MontoInvalidoError(
            (
                f"El monto pagado (${monto:,}) no coincide con el precio del plan "
                f"«{plan.nombre}» (${plan.precio:,})."
            ).replace(",", ".")
        )

    # Bloqueo de la membresía vigente (ACTIVA o CONGELADA) del socio, si existe.
    # La UniqueConstraint del modelo garantiza que hay a lo sumo una.
    membresia_vigente = (
        Membresia.objects.select_for_update()
        .filter(socio=socio, estado__in=[EstadoMembresia.ACTIVA, EstadoMembresia.CONGELADA])
        .first()
    )

    if membresia_vigente is not None:
        membresia_vigente = verificar_vencimiento(membresia_vigente)

    # --- Caso 1: congelada → se rechaza el pago ---
    if membresia_vigente is not None and membresia_vigente.estado == EstadoMembresia.CONGELADA:
        raise MembresiaCongeladaError()

    # --- Caso 2: activa y vigente → se extiende fecha_fin desde esa fecha ---
    if membresia_vigente is not None and membresia_vigente.estado == EstadoMembresia.ACTIVA:
        membresia = membresia_vigente
        membresia.plan = plan
        membresia.fecha_fin = membresia.fecha_fin + timedelta(days=plan.duracion_dias)
        membresia.save(update_fields=["plan", "fecha_fin", "actualizado_en"])
        _registrar_historial(
            membresia,
            EstadoMembresia.ACTIVA,
            EstadoMembresia.ACTIVA,
            autor=registrado_por,
            observacion=f"Renovada con el plan «{plan.nombre}».",
        )
    # --- Caso 3: no hay ninguna vigente (o acaba de quedar VENCIDA) → se crea desde hoy ---
    else:
        hoy = timezone.localdate()
        membresia = Membresia.objects.create(
            socio=socio,
            plan=plan,
            fecha_inicio=hoy,
            fecha_fin=hoy + timedelta(days=plan.duracion_dias),
            estado=EstadoMembresia.ACTIVA,
        )
        _registrar_historial(
            membresia,
            None,
            EstadoMembresia.ACTIVA,
            autor=registrado_por,
            observacion=f"Activada con el plan «{plan.nombre}».",
        )

    return Pago.objects.create(
        socio=socio,
        plan=plan,
        membresia=membresia,
        monto=monto,
        metodo=metodo,
        registrado_por=registrado_por,
    )


# ============================================================
# BLOQUE 4 — CONGELAR / DESCONGELAR
# ============================================================
@transaction.atomic
def congelar(membresia: Membresia, dias: int, autor=None, observacion: str = "") -> Membresia:
    """ACTIVA → CONGELADA. "dias" debe estar dentro del rango configurado por .env."""
    membresia = Membresia.objects.select_for_update().get(pk=membresia.pk)
    membresia = verificar_vencimiento(membresia)

    if membresia.estado != EstadoMembresia.ACTIVA:
        raise TransicionInvalidaError(
            f"Solo se puede congelar una membresía ACTIVA (estado actual: {membresia.get_estado_display()})."
        )

    minimo, maximo = settings.CONGELAMIENTO_DIAS_MIN, settings.CONGELAMIENTO_DIAS_MAX
    if not (minimo <= dias <= maximo):
        raise RangoDeCongelamientoError(f"Los días a congelar deben estar entre {minimo} y {maximo}.")

    membresia.estado = EstadoMembresia.CONGELADA
    membresia.dias_congelados = dias
    membresia.fecha_congelamiento = timezone.localdate()
    membresia.save(update_fields=["estado", "dias_congelados", "fecha_congelamiento", "actualizado_en"])
    _registrar_historial(
        membresia,
        EstadoMembresia.ACTIVA,
        EstadoMembresia.CONGELADA,
        autor=autor,
        observacion=observacion or f"Congelada por {dias} día(s).",
    )
    return membresia


@transaction.atomic
def descongelar(membresia: Membresia, autor=None, observacion: str = "") -> Membresia:
    """CONGELADA → ACTIVA. fecha_fin se extiende por los días que estuvo congelada."""
    membresia = Membresia.objects.select_for_update().get(pk=membresia.pk)

    if membresia.estado != EstadoMembresia.CONGELADA:
        raise TransicionInvalidaError(
            f"Solo se puede descongelar una membresía CONGELADA (estado actual: {membresia.get_estado_display()})."
        )

    membresia.estado = EstadoMembresia.ACTIVA
    membresia.fecha_fin = membresia.fecha_fin + timedelta(days=membresia.dias_congelados)
    membresia.save(update_fields=["estado", "fecha_fin", "actualizado_en"])
    _registrar_historial(
        membresia,
        EstadoMembresia.CONGELADA,
        EstadoMembresia.ACTIVA,
        autor=autor,
        observacion=observacion or "Descongelada; se extendió la fecha de término por los días congelados.",
    )
    return membresia
