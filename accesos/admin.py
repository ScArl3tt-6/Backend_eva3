# ============================================================
# accesos/admin.py — INSTALACIÓN (AFORO) Y REGISTROS DE ACCESO
# RegistroAcceso es un registro de auditoría: se crea solo a través
# de servicios.validar_acceso, nunca a mano, y no se borra.
# Instalacion es una tabla "singleton": el admin impide crear una
# segunda fila y prohíbe borrar la única que debe existir.
# ============================================================

from django.contrib import admin
from django.utils.html import format_html

from .models import Instalacion, RegistroAcceso, ResultadoAcceso


@admin.register(Instalacion)
class InstalacionAdmin(admin.ModelAdmin):
    """Aforo máximo del gimnasio. Edítelo aquí; nunca por archivo .env."""

    list_display = ["nombre", "aforo_maximo", "actualizado_en"]
    readonly_fields = ["actualizado_en"]

    def has_add_permission(self, request):
        # Solo puede existir una fila.
        return not Instalacion.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(RegistroAcceso)
class RegistroAccesoAdmin(admin.ModelAdmin):
    """Bitácora de intentos de acceso: solo lectura, es evidencia de auditoría."""

    list_display = ["socio", "tipo", "resultado_insignia", "motivo", "fecha_hora", "registrado_por"]
    list_filter = ["tipo", "resultado", "fecha_hora"]
    search_fields = ["socio__rut", "socio__usuario__username", "token_intentado", "motivo"]
    ordering = ["-fecha_hora"]
    list_per_page = 50
    date_hierarchy = "fecha_hora"
    readonly_fields = ["socio", "token_intentado", "tipo", "fecha_hora", "resultado", "motivo", "registrado_por"]

    @admin.display(description="resultado")
    def resultado_insignia(self, obj):
        color = "#3f9e84" if obj.resultado == ResultadoAcceso.PERMITIDO else "#d1526a"
        return format_html(
            '<span style="background:{}1a;color:{};padding:.25rem .6rem;border-radius:999px;'
            'font-size:.78rem;font-weight:600;">{}</span>',
            color, color, obj.get_resultado_display(),
        )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
