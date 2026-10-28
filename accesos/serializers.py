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
