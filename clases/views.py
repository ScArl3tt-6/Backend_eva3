# ============================================================
# clases/views.py — TIPOS DE CLASE, CLASES Y RESERVAS (API)
# ============================================================
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from socios.models import Socio
from socios.permisos import EsPropietarioDelSocio
from usuarios.permisos import EsAdministradorORecepcion, EsInstructor, EsSocio

from .models import Clase, Reserva, TipoClase
from .serializers import (
    ClaseSerializer,
    MarcarAsistenciaInputSerializer,
    ReservarClaseInputSerializer,
    ReservaSerializer,
    TipoClaseSerializer,
)
from .servicios import cancelar_clase, cancelar_reserva, marcar_asistencia, reservar_clase


class TipoClaseViewSet(viewsets.ModelViewSet):
    queryset = TipoClase.objects.all()
    serializer_class = TipoClaseSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAuthenticated(), EsAdministradorORecepcion()]
        return super().get_permissions()


class ClaseViewSet(viewsets.ModelViewSet):
    """Clases grupales. Un instructor solo ve las suyas; el resto del personal ve todas."""

    queryset = Clase.objects.select_related("tipo", "instructor").all()
    serializer_class = ClaseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        usuario = self.request.user
        qs = super().get_queryset()
        if usuario.es_instructor:
            return qs.filter(instructor=usuario)
        return qs

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy", "cancelar"):
            return [IsAuthenticated(), EsAdministradorORecepcion()]
        return super().get_permissions()

    @action(detail=True, methods=["post"])
    def cancelar(self, request, pk=None):
        clase = cancelar_clase(self.get_object(), autor=request.user)
        return Response(ClaseSerializer(clase).data)


class ReservaViewSet(viewsets.ModelViewSet):
    """Reservas con cupos y lista de espera. El socio solo reserva/cancela las propias."""

    queryset = Reserva.objects.select_related("clase", "socio__usuario").all()
    serializer_class = ReservaSerializer
    permission_classes = [IsAuthenticated, EsPropietarioDelSocio]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        usuario = self.request.user
        qs = super().get_queryset()
        if usuario.es_administrador or usuario.es_recepcion:
            return qs
        if usuario.es_instructor:
            return qs.filter(clase__instructor=usuario)
        if usuario.es_socio:
            return qs.filter(socio__usuario=usuario)
        return qs.none()

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated(), EsSocio()]
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        entrada = ReservarClaseInputSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        socio = get_object_or_404(Socio, usuario=request.user)
        reserva = reservar_clase(socio, entrada.validated_data["clase"])
        return Response(ReservaSerializer(reserva).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def cancelar(self, request, pk=None):
        reserva = cancelar_reserva(self.get_object(), autor=request.user)
        return Response(ReservaSerializer(reserva).data)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, EsInstructor])
    def asistencia(self, request, pk=None):
        reserva = self.get_object()
        if reserva.clase.instructor_id != request.user.id:
            raise PermissionDenied("Esta clase no está a tu cargo.")

        entrada = MarcarAsistenciaInputSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        reserva = marcar_asistencia(reserva, asistio=entrada.validated_data["asistio"])
        return Response(ReservaSerializer(reserva).data)
