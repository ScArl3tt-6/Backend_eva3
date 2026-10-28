# ============================================================
# socios/views.py — API DEL SOCIO
# Administración/recepción ven y editan todos los socios; un socio
# solo puede ver su propio perfil (nunca el de otro).
# ============================================================
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from usuarios.permisos import EsAdministradorORecepcion

from .models import Socio
from .permisos import EsPropietarioDelSocio
from .serializers import SocioSerializer


class SocioViewSet(viewsets.ModelViewSet):
    """CRUD de socios con control de acceso a nivel de objeto."""

    queryset = Socio.objects.select_related("usuario").all()
    serializer_class = SocioSerializer
    permission_classes = [IsAuthenticated, EsPropietarioDelSocio]

    def get_queryset(self):
        usuario = self.request.user
        qs = super().get_queryset()
        if usuario.es_administrador or usuario.es_recepcion:
            return qs
        return qs.filter(usuario=usuario)

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAuthenticated(), EsAdministradorORecepcion()]
        return super().get_permissions()
