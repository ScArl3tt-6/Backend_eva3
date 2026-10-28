# ============================================================
# membresias/serializers.py — PLANES, MEMBRESÍAS Y PAGOS (API)
# Membresia y Pago son de solo lectura por serializer de modelo: se
# crean y modifican únicamente a través de servicios.py (pago,
# congelar, descongelar), nunca por un POST/PUT genérico que
# pudiera saltarse esas reglas.
# ============================================================
from rest_framework import serializers

from socios.models import Socio

from .models import HistorialEstadoMembresia, Membresia, MetodoPago, Pago, Plan


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = ["id", "nombre", "descripcion", "precio", "duracion_dias", "clases_por_semana", "activo"]


class HistorialEstadoMembresiaSerializer(serializers.ModelSerializer):
    class Meta:
        model = HistorialEstadoMembresia
        fields = ["id", "estado_anterior", "estado_nuevo", "autor", "fecha", "observacion"]


class MembresiaSerializer(serializers.ModelSerializer):
    plan_nombre = serializers.CharField(source="plan.nombre", read_only=True)
    socio_nombre = serializers.CharField(source="socio.usuario.nombre_completo", read_only=True)

    class Meta:
        model = Membresia
        fields = [
            "id", "socio", "socio_nombre", "plan", "plan_nombre", "fecha_inicio", "fecha_fin",
            "estado", "dias_congelados", "fecha_congelamiento", "creado_en",
        ]
        read_only_fields = fields  # se modifica solo vía servicios.registrar_pago/congelar/descongelar


class CongelarInputSerializer(serializers.Serializer):
    dias = serializers.IntegerField(min_value=1)


class PagoSerializer(serializers.ModelSerializer):
    socio_nombre = serializers.CharField(source="socio.usuario.nombre_completo", read_only=True)

    class Meta:
        model = Pago
        fields = [
            "id", "socio", "socio_nombre", "plan", "membresia", "monto", "metodo", "fecha",
            "registrado_por", "comprobante",
        ]
        read_only_fields = ["id", "membresia", "fecha", "registrado_por", "comprobante"]


class RegistrarPagoInputSerializer(serializers.Serializer):
    """Entrada de POST /api/pagos/: dispara membresias.servicios.registrar_pago."""

    socio = serializers.PrimaryKeyRelatedField(queryset=Socio.objects.all())
    plan = serializers.PrimaryKeyRelatedField(queryset=Plan.objects.all())
    monto = serializers.IntegerField(min_value=1)
    metodo = serializers.ChoiceField(choices=MetodoPago.choices)
