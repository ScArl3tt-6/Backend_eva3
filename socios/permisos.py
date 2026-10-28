# ============================================================
# socios/permisos.py — PERMISO DE OBJETO: DUEÑO DEL SOCIO
# Responsabilidad: garantizar que un socio jamás vea ni modifique
# datos de otro socio. Lo reutilizan membresias, accesos y clases
# porque todos sus modelos cuelgan de un Socio (directamente o por
# un campo "socio"), evitando repetir esta comparación en cada app.
# ============================================================

from rest_framework.permissions import BasePermission

from .models import Socio


class EsPropietarioDelSocio(BasePermission):
    """Autoriza al propio socio (o a administración/recepción) sobre el objeto."""

    message = "Este recurso pertenece a otro socio."

    def has_object_permission(self, request, view, obj) -> bool:
        usuario = request.user
        if not usuario.is_authenticated:
            return False

        if usuario.es_administrador or usuario.es_recepcion:
            return True

        socio = obj if isinstance(obj, Socio) else getattr(obj, "socio", None)
        return socio is not None and socio.usuario_id == usuario.id
