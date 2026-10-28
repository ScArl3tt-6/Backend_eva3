# ============================================================
# socios/serializers.py — SERIALIZADOR DEL SOCIO (API)
# ============================================================
from rest_framework import serializers

from .models import Socio


class SocioSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.CharField(source="usuario.nombre_completo", read_only=True)
    username = serializers.CharField(source="usuario.username", read_only=True)

    class Meta:
        model = Socio
        fields = [
            "id", "usuario", "username", "nombre_completo", "rut", "telefono",
            "contacto_emergencia_nombre", "contacto_emergencia_telefono", "token_qr", "creado_en",
        ]
        read_only_fields = ["id", "token_qr", "creado_en"]
