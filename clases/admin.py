# ============================================================
# clases/admin.py — TIPOS DE CLASE, CLASES Y RESERVAS
# Las reservas se muestran como inline dentro de la clase (pedido
# de la pauta) y además tienen su propio listado con acciones
# masivas de asistencia, útiles para revisar varias clases a la vez.
# ============================================================

from django.contrib import admin
from django.utils.html import format_html

from .models import Clase, EstadoClase, EstadoReserva, Reserva, TipoClase
from .servicios import cancelar_clase, marcar_asistencia

COLOR_POR_ESTADO_RESERVA = {
    EstadoReserva.CONFIRMADA: "#3f9e84",
    EstadoReserva.EN_ESPERA: "#c98a1e",
    EstadoReserva.CANCELADA: "#d1526a",
    EstadoReserva.ASISTIO: "#3f83c4",
    EstadoReserva.NO_ASISTIO: "#6a7194",
}

COLOR_POR_ESTADO_CLASE = {
    EstadoClase.PROGRAMADA: "#3f83c4",
    EstadoClase.EN_CURSO: "#3f9e84",
    EstadoClase.FINALIZADA: "#6a7194",
    EstadoClase.CANCELADA: "#d1526a",
}


def _insignia(color, etiqueta):
    return format_html(
        '<span style="background:{}1a;color:{};padding:.25rem .6rem;border-radius:999px;'
        'font-size:.78rem;font-weight:600;">{}</span>',
        color, color, etiqueta,
    )


@admin.register(TipoClase)
class TipoClaseAdmin(admin.ModelAdmin):
    list_display = ["nombre"]
    search_fields = ["nombre"]


class ReservaInline(admin.TabularInline):
    """Reservas de la clase: confirmadas, en espera y su desenlace."""

    model = Reserva
    extra = 0
    can_delete = False
    fields = ["socio", "estado", "posicion_espera", "creada_en"]
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Clase)
class ClaseAdmin(admin.ModelAdmin):
    list_display = ["tipo", "instructor", "sala", "inicio", "estado_insignia", "cupos_legibles"]
    list_filter = ["estado", "tipo", "instructor"]
    search_fields = ["tipo__nombre", "sala", "instructor__username"]
    ordering = ["-inicio"]
    list_per_page = 25
    date_hierarchy = "inicio"
    autocomplete_fields = ["tipo", "instructor"]
    readonly_fields = ["creado_en", "actualizado_en"]
    inlines = [ReservaInline]
    actions = ["accion_cancelar_clase"]

    @admin.display(description="estado")
    def estado_insignia(self, obj):
        return _insignia(COLOR_POR_ESTADO_CLASE.get(obj.estado, "#6a7194"), obj.get_estado_display())

    @admin.display(description="cupos")
    def cupos_legibles(self, obj):
        return f"{obj.cupos_confirmados}/{obj.cupo_maximo} (espera: {obj.en_lista_de_espera})"

    @admin.action(description="Cancelar clase (cancela también sus reservas activas)")
    def accion_cancelar_clase(self, request, queryset):
        total = 0
        for clase in queryset.exclude(estado=EstadoClase.CANCELADA):
            cancelar_clase(clase, autor=request.user)
            total += 1
        self.message_user(request, f"Clases canceladas: {total}.")


@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ["socio", "clase", "estado_insignia", "posicion_espera", "creada_en"]
    list_filter = ["estado", "clase__tipo"]
    search_fields = ["socio__rut", "socio__usuario__username", "clase__tipo__nombre"]
    ordering = ["-creada_en"]
    list_per_page = 25
    autocomplete_fields = ["clase", "socio"]
    readonly_fields = ["creada_en", "actualizada_en"]
    actions = ["accion_marcar_asistio", "accion_marcar_no_asistio"]

    @admin.display(description="estado")
    def estado_insignia(self, obj):
        return _insignia(COLOR_POR_ESTADO_RESERVA.get(obj.estado, "#6a7194"), obj.get_estado_display())

    def _marcar(self, request, queryset, asistio):
        marcadas, omitidas = 0, 0
        for reserva in queryset:
            try:
                marcar_asistencia(reserva, asistio=asistio)
                marcadas += 1
            except Exception:
                omitidas += 1
        mensaje = f"Marcadas: {marcadas}."
        if omitidas:
            mensaje += f" Omitidas (estado o clase no corresponde): {omitidas}."
        self.message_user(request, mensaje)

    @admin.action(description="Marcar asistencia: ASISTIÓ")
    def accion_marcar_asistio(self, request, queryset):
        self._marcar(request, queryset, asistio=True)

    @admin.action(description="Marcar asistencia: NO ASISTIÓ")
    def accion_marcar_no_asistio(self, request, queryset):
        self._marcar(request, queryset, asistio=False)
