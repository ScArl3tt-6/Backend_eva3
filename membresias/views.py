# ============================================================
# membresias/views.py — PLANES, MEMBRESÍAS Y PAGOS (API)
# ============================================================
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from usuarios.permisos import EsAdministradorORecepcion, EsAdministradorOSoloLectura

from .models import Membresia, Pago, Plan
from .serializers import (
    CongelarInputSerializer,
    MembresiaSerializer,
    PagoSerializer,
    PlanSerializer,
    RegistrarPagoInputSerializer,
)
from .servicios import congelar, descongelar, registrar_pago


class PlanViewSet(viewsets.ModelViewSet):
    """Catálogo de planes. Lectura para cualquier autenticado; escritura solo administrador."""

    queryset = Plan.objects.all()
    serializer_class = PlanSerializer
    permission_classes = [IsAuthenticated, EsAdministradorOSoloLectura]


class MembresiaViewSet(viewsets.ReadOnlyModelViewSet):
    """Las membresías se crean/modifican solo vía pago, congelar o descongelar."""

    queryset = Membresia.objects.select_related("socio__usuario", "plan").all()
    serializer_class = MembresiaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        usuario = self.request.user
        qs = super().get_queryset()
        if usuario.es_administrador or usuario.es_recepcion:
            return qs
        if usuario.es_socio:
            return qs.filter(socio__usuario=usuario)
        return qs.none()

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, EsAdministradorORecepcion])
    def congelar(self, request, pk=None):
        entrada = CongelarInputSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        membresia = congelar(self.get_object(), dias=entrada.validated_data["dias"], autor=request.user)
        return Response(MembresiaSerializer(membresia).data)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, EsAdministradorORecepcion])
    def descongelar(self, request, pk=None):
        membresia = descongelar(self.get_object(), autor=request.user)
        return Response(MembresiaSerializer(membresia).data)


class PagoViewSet(viewsets.ModelViewSet):
    """Registro de auditoría: no se edita ni se borra (ver has_delete en el admin)."""

    queryset = Pago.objects.select_related("socio__usuario", "plan", "membresia").all()
    serializer_class = PagoSerializer
    http_method_names = ["get", "post", "head", "options"]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        usuario = self.request.user
        qs = super().get_queryset()
        if usuario.es_administrador or usuario.es_recepcion:
            return qs
        if usuario.es_socio:
            return qs.filter(socio__usuario=usuario)
        return qs.none()

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated(), EsAdministradorORecepcion()]
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        entrada = RegistrarPagoInputSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        pago = registrar_pago(
            socio=entrada.validated_data["socio"],
            plan=entrada.validated_data["plan"],
            monto=entrada.validated_data["monto"],
            metodo=entrada.validated_data["metodo"],
            registrado_por=request.user,
        )
        return Response(PagoSerializer(pago).data, status=status.HTTP_201_CREATED)
