# ============================================================
# core/excepciones.py — ERRORES DE NEGOCIO Y MANEJADOR JSON DE LA API
# Responsabilidad: definir la excepción base que lanzan TODOS los
# servicios.py del proyecto (membresias, accesos, clases) y el
# EXCEPTION_HANDLER de DRF que traduce cualquier error a un formato
# uniforme en español:
#   {"error": true, "mensaje": "...", "detalle": ...}
#
# Las vistas HTML atrapan ErrorDeNegocio y muestran exc.mensaje como
# mensaje flash; la API usa exc.codigo_http para el status HTTP. Así
# la regla de negocio se escribe una sola vez y sirve a ambos canales.
# ============================================================

from django.core.exceptions import PermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler


# ============================================================
# BLOQUE 1 — EXCEPCIÓN BASE DE NEGOCIO
# ============================================================
class ErrorDeNegocio(Exception):
    """Regla de negocio incumplida, con mensaje en español y código HTTP."""

    codigo_http = status.HTTP_400_BAD_REQUEST
    mensaje_por_defecto = "No fue posible completar la operación."

    def __init__(self, mensaje=None, detalle=None):
        self.mensaje = mensaje or self.mensaje_por_defecto
        self.detalle = detalle
        super().__init__(self.mensaje)


# ============================================================
# BLOQUE 2 — MENSAJES GENERALES POR TIPO DE ERROR DE DRF
# ============================================================
MENSAJES = {
    exceptions.NotAuthenticated: "Debes iniciar sesión: envía un token JWT válido en el encabezado Authorization (Bearer).",
    exceptions.AuthenticationFailed: "El token enviado no es válido o expiró.",
    exceptions.PermissionDenied: "No tienes permisos para realizar esta acción con tu rol.",
    exceptions.NotFound: "El recurso solicitado no existe.",
    exceptions.MethodNotAllowed: "Método HTTP no permitido en este endpoint.",
    exceptions.ValidationError: "Los datos enviados no son válidos.",
    exceptions.ParseError: "El cuerpo de la petición no es un JSON válido.",
    exceptions.Throttled: "Demasiadas peticiones. Intenta nuevamente en unos segundos.",
    exceptions.UnsupportedMediaType: "Tipo de contenido no soportado.",
}


def _cuerpo(mensaje, detalle=None):
    """Arma el cuerpo JSON uniforme de error."""
    return {"error": True, "mensaje": mensaje, "detalle": detalle}


# ============================================================
# BLOQUE 3 — MANEJADOR DE EXCEPCIONES DE DRF
# ============================================================
def manejador_excepciones_api(exc, context):
    """Traduce cualquier excepción de la API a una respuesta JSON uniforme."""
    # --- Reglas de negocio propias (409 sin cupo/aforo, 400 transición inválida, etc.) ---
    if isinstance(exc, ErrorDeNegocio):
        return Response(_cuerpo(exc.mensaje, exc.detalle), status=exc.codigo_http)

    # --- Validaciones de modelo (full_clean/save) que llegan como ValidationError de Django ---
    if isinstance(exc, DjangoValidationError):
        detalle = exc.message_dict if hasattr(exc, "error_dict") else exc.messages
        return Response(_cuerpo("Los datos enviados no son válidos.", detalle), status=400)

    # --- Violaciones de integridad (UniqueConstraint/CheckConstraint) como última barrera ---
    if isinstance(exc, IntegrityError):
        return Response(
            _cuerpo("La operación viola una regla de integridad de la base de datos.", str(exc).splitlines()[0]),
            status=status.HTTP_409_CONFLICT,
        )

    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, PermissionDenied):
        exc = exceptions.PermissionDenied()

    response = exception_handler(exc, context)
    if response is None:
        return None

    mensaje = next((m for tipo, m in MENSAJES.items() if isinstance(exc, tipo)), None)
    detalle = response.data
    if isinstance(detalle, dict) and set(detalle.keys()) == {"detail"}:
        detalle = detalle["detail"]
    if mensaje is None:
        mensaje = str(detalle) if isinstance(detalle, str) else "Ocurrió un error al procesar la petición."

    response.data = _cuerpo(mensaje, detalle)
    return response
