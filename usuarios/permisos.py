# ============================================================
# usuarios/permisos.py — PERMISOS REUTILIZABLES POR ROL
# Responsabilidad: concentrar las comprobaciones de rol que usan
# las vistas de la API de todas las apps, para no repetirlas.
#
# Defensa en profundidad: se exige que coincidan el claim "rol" del
# token JWT firmado Y el rol guardado en la base de datos, además de
# que la cuenta siga activa. Así, si alguien es degradado o
# desactivado, su token vigente deja de tener efecto sin esperar a
# que expire.
#
# Los permisos de OBJETO (p. ej. "esta reserva es de este socio")
# viven en el permisos.py de cada app dueña del modelo, para no
# generar dependencias circulares entre apps.
# ============================================================

from rest_framework.permissions import SAFE_METHODS, BasePermission

from .models import Rol


def _tiene_rol(request, roles_esperados) -> bool:
    """True si el usuario autenticado, activo, tiene uno de los roles pedidos."""
    usuario = getattr(request, "user", None)

    if usuario is None or not usuario.is_authenticated or not usuario.is_active:
        return False

    if usuario.rol not in roles_esperados:
        return False

    # Si la petición llegó con un token JWT, su claim debe concordar.
    token = getattr(request, "auth", None)
    if token is not None and hasattr(token, "get"):
        rol_del_token = token.get("rol")
        if rol_del_token is not None and rol_del_token not in roles_esperados:
            return False

    return True


class EsAdministrador(BasePermission):
    """Concede acceso únicamente al rol Administrador."""

    message = "Solo un administrador puede realizar esta acción."

    def has_permission(self, request, view) -> bool:
        return _tiene_rol(request, {Rol.ADMINISTRADOR})


class EsRecepcion(BasePermission):
    """Concede acceso únicamente al rol Recepción."""

    message = "Esta acción está reservada a recepción."

    def has_permission(self, request, view) -> bool:
        return _tiene_rol(request, {Rol.RECEPCION})


class EsInstructor(BasePermission):
    """Concede acceso únicamente al rol Instructor."""

    message = "Esta acción está reservada a los instructores."

    def has_permission(self, request, view) -> bool:
        return _tiene_rol(request, {Rol.INSTRUCTOR})


class EsSocio(BasePermission):
    """Concede acceso únicamente al rol Socio."""

    message = "Esta acción está reservada a los socios."

    def has_permission(self, request, view) -> bool:
        return _tiene_rol(request, {Rol.SOCIO})


class EsAdministradorORecepcion(BasePermission):
    """Concede acceso a quien registra socios, pagos y membresías."""

    message = "Esta acción está reservada a administración o recepción."

    def has_permission(self, request, view) -> bool:
        return _tiene_rol(request, {Rol.ADMINISTRADOR, Rol.RECEPCION})


class EsAdministradorOSoloLectura(BasePermission):
    """Cualquier persona autenticada puede leer; solo el administrador puede escribir."""

    message = "Solo un administrador puede modificar este recurso."

    def has_permission(self, request, view) -> bool:
        usuario = getattr(request, "user", None)
        if usuario is None or not usuario.is_authenticated or not usuario.is_active:
            return False
        if request.method in SAFE_METHODS:
            return True
        return _tiene_rol(request, {Rol.ADMINISTRADOR})


class EsPersonalDelGimnasio(BasePermission):
    """Concede acceso a cualquier rol que no sea Socio (personal interno)."""

    message = "Esta acción está reservada al personal del gimnasio."

    def has_permission(self, request, view) -> bool:
        return _tiene_rol(request, {Rol.ADMINISTRADOR, Rol.RECEPCION, Rol.INSTRUCTOR})
