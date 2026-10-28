# ============================================================
# accesos/serializers.py — REGISTROS DE ACCESO Y VALIDACIÓN (API)
# ============================================================
from rest_framework import serializers

from .models import RegistroAcceso, TipoAcceso


class RegistroAccesoSerializer(serializers.ModelSerializer):
    socio_nombre = serializers.CharField(source="socio.usuario.nombre_completo", read_only=True, default=None)
    socio_rut = serializers.CharField(source="socio.rut", read_only=True, default=None)

    class Meta:
        model = RegistroAcceso
        fields = ["id", "socio", "socio_nombre", "socio_rut", "tipo", "fecha_hora", "resultado", "motivo", "registrado_por"]
        read_only_fields = fields


class ValidarAccesoInputSerializer(serializers.Serializer):
    """Entrada de POST /api/accesos/validar/: token escaneado (cámara o texto) + tipo."""

    token = serializers.CharField()
    tipo = serializers.ChoiceField(choices=TipoAcceso.choices)


class ClaseResumenAforoSerializer(serializers.Serializer):
    """Resumen de una clase de hoy para el dashboard de aforo."""

    id = serializers.IntegerField()
    tipo = serializers.CharField()
    instructor = serializers.CharField()
    inicio = serializers.DateTimeField()
    cupo_maximo = serializers.IntegerField()
    cupos_confirmados = serializers.IntegerField()
    en_lista_de_espera = serializers.IntegerField()


class AforoSerializer(serializers.Serializer):
    """Salida de GET /api/aforo/: lo que consume el dashboard con fetch cada 5s."""

    ocupacion_actual = serializers.IntegerField()
    capacidad = serializers.IntegerField()
    porcentaje = serializers.IntegerField()
    ultimos_accesos = RegistroAccesoSerializer(many=True)
    denegados_hoy = RegistroAccesoSerializer(many=True)
    clases_hoy = ClaseResumenAforoSerializer(many=True)
