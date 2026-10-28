# ============================================================
# membresias/admin.py — PLANES, MEMBRESÍAS, PAGOS E HISTORIAL
# Pago es un registro de auditoría: no se crea ni se borra desde el
# Admin (se crea solo a través de servicios.registrar_pago, que es
# quien mueve la membresía en la misma transacción). Por eso todos
# sus campos son de solo lectura y has_add/has_delete devuelven False.
# ============================================================

from django.contrib import admin
from django.utils.html import format_html

from .models import EstadoMembresia, HistorialEstadoMembresia, Membresia, Pago, Plan
from .servicios import descongelar

COLOR_POR_ESTADO = {
    EstadoMembresia.ACTIVA: "#3f9e84",
    EstadoMembresia.VENCIDA: "#d1526a",
    EstadoMembresia.CONGELADA: "#3f83c4",
}


def _insignia_estado(estado, etiqueta):
    color = COLOR_POR_ESTADO.get(estado, "#6a7194")
    return format_html(
        '<span style="background:{}1a;color:{};padding:.25rem .6rem;border-radius:999px;'
        'font-size:.78rem;font-weight:600;">{}</span>',
        color, color, etiqueta,
    )


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ["nombre", "precio_legible", "duracion_dias", "clases_por_semana", "activo"]
    list_filter = ["activo"]
    search_fields = ["nombre"]
    ordering = ["precio"]

    @admin.display(description="precio")
    def precio_legible(self, obj):
        return f"${obj.precio:,}".replace(",", ".")


class HistorialEstadoMembresiaInline(admin.TabularInline):
    model = HistorialEstadoMembresia
    extra = 0
    can_delete = False
    fields = ["fecha", "estado_anterior", "estado_nuevo", "autor", "observacion"]
    readonly_fields = fields
    ordering = ["fecha"]

    def has_add_permission(self, request, obj=None):
        return False


class PagoInline(admin.TabularInline):
    """Pagos que dieron origen o renovaron esta membresía (solo lectura)."""

    model = Pago
    extra = 0
    can_delete = False
    fields = ["comprobante", "monto", "metodo", "fecha", "registrado_por"]
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Membresia)
class MembresiaAdmin(admin.ModelAdmin):
    list_display = ["socio", "plan", "estado_insignia", "fecha_inicio", "fecha_fin", "dias_congelados"]
    list_filter = ["estado", "plan"]
    search_fields = ["socio__rut", "socio__usuario__username", "socio__usuario__first_name", "socio__usuario__last_name"]
    ordering = ["-fecha_inicio"]
    list_per_page = 25
    date_hierarchy = "fecha_inicio"
    autocomplete_fields = ["socio", "plan"]
    readonly_fields = ["creado_en", "actualizado_en"]
    inlines = [PagoInline, HistorialEstadoMembresiaInline]
    actions = ["accion_descongelar"]

    @admin.display(description="estado")
    def estado_insignia(self, obj):
        return _insignia_estado(obj.estado, obj.get_estado_display())

    @admin.action(description="Descongelar (extiende fecha_fin por los días congelados)")
    def accion_descongelar(self, request, queryset):
        descongeladas = 0
        for membresia in queryset.filter(estado=EstadoMembresia.CONGELADA):
            descongelar(membresia, autor=request.user, observacion="Descongelada desde el Django Admin.")
            descongeladas += 1
        self.message_user(request, f"Membresías descongeladas: {descongeladas}.")


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    """Pagos: registro de auditoría. Se crean solo vía servicios.registrar_pago."""

    list_display = ["comprobante", "socio", "plan", "monto_legible", "metodo", "fecha", "registrado_por"]
    list_filter = ["metodo", "fecha", "plan"]
    search_fields = ["comprobante", "socio__rut", "socio__usuario__username"]
    ordering = ["-fecha"]
    list_per_page = 25
    date_hierarchy = "fecha"
    readonly_fields = ["socio", "plan", "membresia", "monto", "metodo", "fecha", "registrado_por", "comprobante"]

    @admin.display(description="monto")
    def monto_legible(self, obj):
        return f"${obj.monto:,}".replace(",", ".")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(HistorialEstadoMembresia)
class HistorialEstadoMembresiaAdmin(admin.ModelAdmin):
    list_display = ["membresia", "estado_anterior", "estado_nuevo", "autor", "fecha"]
    list_filter = ["estado_nuevo", "estado_anterior", "fecha"]
    search_fields = ["membresia__socio__rut", "observacion"]
    ordering = ["-fecha"]
    readonly_fields = ["membresia", "estado_anterior", "estado_nuevo", "autor", "fecha", "observacion"]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
