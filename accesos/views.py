# ============================================================
# accesos/views.py — VALIDACIÓN DE ACCESO Y DASHBOARD DE AFORO (API)
# ============================================================
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from clases.models import Clase
from usuarios.permisos import EsAdministradorORecepcion

from .models import Instalacion, RegistroAcceso, ResultadoAcceso
from .serializers import RegistroAccesoSerializer, ValidarAccesoInputSerializer
from .servicios import ocupacion_actual, validar_acceso


class RegistroAccesoViewSet(viewsets.ReadOnlyModelViewSet):
    """Bitácora de accesos: cada socio ve solo la suya; el personal ve todo."""

    queryset = RegistroAcceso.objects.select_related("socio__usuario", "registrado_por").all()
    serializer_class = RegistroAccesoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        usuario = self.request.user
        qs = super().get_queryset()
        if usuario.es_administrador or usuario.es_recepcion:
            return qs
        if usuario.es_socio:
            return qs.filter(socio__usuario=usuario)
        return qs.none()


class ValidarAccesoView(APIView):
    """POST /api/accesos/validar/ — pantalla de recepción (cámara o texto)."""

    permission_classes = [IsAuthenticated, EsAdministradorORecepcion]

    def post(self, request):
        entrada = ValidarAccesoInputSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        registro = validar_acceso(
            token=entrada.validated_data["token"],
            tipo=entrada.validated_data["tipo"],
            registrado_por=request.user,
        )
        return Response(RegistroAccesoSerializer(registro).data, status=status.HTTP_201_CREATED)


class AforoView(APIView):
    """GET /api/aforo/ — datos del dashboard en tiempo real (fetch cada 5s desde la web)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        instalacion = Instalacion.obtener()
        ocupacion = ocupacion_actual()
        porcentaje = round((ocupacion / instalacion.aforo_maximo) * 100) if instalacion.aforo_maximo else 0

        ultimos = RegistroAcceso.objects.select_related("socio__usuario").order_by("-fecha_hora")[:10]
        hoy = timezone.localdate()
        denegados_hoy = (
            RegistroAcceso.objects.filter(resultado=ResultadoAcceso.DENEGADO, fecha_hora__date=hoy)
            .select_related("socio__usuario")
            .order_by("-fecha_hora")
        )
        clases_hoy = Clase.objects.filter(inicio__date=hoy).select_related("tipo", "instructor")

        return Response({
            "ocupacion_actual": ocupacion,
            "capacidad": instalacion.aforo_maximo,
            "porcentaje": porcentaje,
            "ultimos_accesos": RegistroAccesoSerializer(ultimos, many=True).data,
            "denegados_hoy": RegistroAccesoSerializer(denegados_hoy, many=True).data,
            "clases_hoy": [
                {
                    "id": clase.id,
                    "tipo": clase.tipo.nombre,
                    "instructor": clase.instructor.nombre_completo,
                    "inicio": clase.inicio,
                    "cupo_maximo": clase.cupo_maximo,
                    "cupos_confirmados": clase.cupos_confirmados,
                    "en_lista_de_espera": clase.en_lista_de_espera,
                }
                for clase in clases_hoy
            ],
        })
