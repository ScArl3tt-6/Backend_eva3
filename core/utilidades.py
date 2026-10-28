# ============================================================
# core/utilidades.py — DECORADOR DE PERMISOS PARA VISTAS WEB
# Responsabilidad: exigir sesión iniciada Y un rol concreto en las
# pantallas HTML, con el mismo resultado (403 con la plantilla
# propia) que usa la API vía DRF. Evita repetir la comprobación de
# rol en cada vista de cada app.
# ============================================================
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def requiere_rol(*roles):
    """Exige login y que request.user.rol esté entre los roles permitidos."""

    def decorador(vista):
        @wraps(vista)
        @login_required
        def envoltura(request, *args, **kwargs):
            if request.user.rol not in roles:
                raise PermissionDenied("Tu rol no tiene acceso a esta pantalla.")
            return vista(request, *args, **kwargs)

        return envoltura

    return decorador
