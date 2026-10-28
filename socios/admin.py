# ============================================================
# socios/admin.py — REGISTRO DEL SOCIO EN DJANGO ADMIN
# Muestra las membresías y los pagos del socio como inlines de solo
# lectura (se crean siempre vía membresias.servicios.registrar_pago,
# nunca a mano desde aquí).
# ============================================================

from django.contrib import admin

from membresias.models import Membresia, Pago

from .models import Socio


class MembresiaInline(admin.TabularInline):
    model = Membresia
    extra = 0
    can_delete = False
    fields = ["plan", "estado", "fecha_inicio", "fecha_fin", "dias_congelados"]
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


class PagoInline(admin.TabularInline):
    model = Pago
    extra = 0
    can_delete = False
    fields = ["comprobante", "plan", "monto", "metodo", "fecha"]
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Socio)
class SocioAdmin(admin.ModelAdmin):
    """Administración de socios: identidad, contacto, token QR, membresías y pagos."""

    list_display = ["rut", "nombre_completo_admin", "telefono", "contacto_emergencia_nombre", "creado_en"]
    list_filter = ["creado_en"]
    search_fields = ["rut", "usuario__username", "usuario__first_name", "usuario__last_name", "usuario__email"]
    ordering = ["usuario__username"]
    list_per_page = 25
    date_hierarchy = "creado_en"
    autocomplete_fields = ["usuario"]
    readonly_fields = ["token_qr", "creado_en", "actualizado_en"]
    inlines = [MembresiaInline, PagoInline]

    fieldsets = (
        ("Identidad", {"fields": ("usuario", "rut")}),
        ("Contacto", {"fields": ("telefono", "contacto_emergencia_nombre", "contacto_emergencia_telefono")}),
        ("Acceso por QR", {
            "fields": ("token_qr",),
            "description": "Para invalidar el QR actual, use la acción «Regenerar token QR».",
        }),
        ("Auditoría", {"fields": ("creado_en", "actualizado_en")}),
    )

    actions = ["regenerar_token_qr"]

    @admin.display(description="socio")
    def nombre_completo_admin(self, obj):
        return obj.usuario.nombre_completo

    @admin.action(description="Regenerar token QR (invalida el anterior de inmediato)")
    def regenerar_token_qr(self, request, queryset):
        for socio in queryset:
            socio.regenerar_token_qr()
        self.message_user(request, f"Token QR regenerado para {queryset.count()} socio(s).")
