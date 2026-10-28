# ============================================================
# clases/serializers.py — TIPOS DE CLASE, CLASES Y RESERVAS (API)
# ============================================================
from rest_framework import serializers

from .models import Clase, Reserva, TipoClase


class TipoClaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoClase
        fields = ["id", "nombre", "descripcion"]


class ClaseSerializer(serializers.ModelSerializer):
    tipo_nombre = serializers.CharField(source="tipo.nombre", read_only=True)
    instructor_nombre = serializers.CharField(source="instructor.nombre_completo", read_only=True)
    cupos_confirmados = serializers.IntegerField(read_only=True)
    en_lista_de_espera = serializers.IntegerField(read_only=True)

    class Meta:
        model = Clase
        fields = [
            "id", "tipo", "tipo_nombre", "instructor", "instructor_nombre", "sala", "inicio", "fin",
            "cupo_maximo", "estado", "cupos_confirmados", "en_lista_de_espera",
        ]


class ReservaSerializer(serializers.ModelSerializer):
    socio_nombre = serializers.CharField(source="socio.usuario.nombre_completo", read_only=True)
    clase_info = serializers.CharField(source="clase.__str__", read_only=True)

    class Meta:
        model = Reserva
        fields = ["id", "clase", "clase_info", "socio", "socio_nombre", "estado", "posicion_espera", "creada_en"]
        read_only_fields = ["id", "socio", "estado", "posicion_espera", "creada_en"]


class ReservarClaseInputSerializer(serializers.Serializer):
    clase = serializers.PrimaryKeyRelatedField(queryset=Clase.objects.all())


class MarcarAsistenciaInputSerializer(serializers.Serializer):
    asistio = serializers.BooleanField()
