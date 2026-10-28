# ============================================================
# usuarios/admin.py — REGISTRO DEL USUARIO EN DJANGO ADMIN
# Se extiende UserAdmin (no se reemplaza) para conservar los
# formularios probados de cambio de contraseña y permisos, y se le
# agrega el campo "rol" con una insignia de color.
# ============================================================

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html

from .models import Rol, Usuario

COLOR_POR_ROL = {
    Rol.ADMINISTRADOR: "#6f5fc0",
    Rol.RECEPCION: "#3da8a4",
    Rol.INSTRUCTOR: "#3f83c4",
    Rol.SOCIO: "#4c63d2",
}


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    """Administración de usuarios: identidad, rol y estado de la cuenta."""

    list_display = ["username", "nombre_completo_admin", "email", "rol_insignia", "is_active", "last_login"]
    list_filter = ["rol", "is_active", "is_staff"]
    search_fields = ["username", "first_name", "last_name", "email"]
    ordering = ["username"]
    list_per_page = 25
    date_hierarchy = "creado_en"
    readonly_fields = ["creado_en", "actualizado_en", "last_login", "date_joined"]

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Datos personales", {"fields": ("first_name", "last_name", "email", "telefono")}),
        ("Rol y permisos", {
            "fields": ("rol", "is_active", "is_staff", "is_superuser", "groups", "user_permissions"),
            "description": "is_staff se sincroniza solo con rol=ADMINISTRADOR; no se edita a mano.",
        }),
        ("Auditoría", {"fields": ("last_login", "date_joined", "creado_en", "actualizado_en")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "email", "rol", "password1", "password2"),
        }),
    )

    @admin.display(description="nombre")
    def nombre_completo_admin(self, obj):
        return obj.nombre_completo

    @admin.display(description="rol")
    def rol_insignia(self, obj):
        color = COLOR_POR_ROL.get(obj.rol, "#6a7194")
        return format_html(
            '<span style="background:{}1a;color:{};padding:.25rem .6rem;border-radius:999px;'
            'font-size:.78rem;font-weight:600;">{}</span>',
            color, color, obj.get_rol_display(),
        )

    def has_delete_permission(self, request, obj=None):
        """Las personas no se borran: se desactivan con is_active=False."""
        return False
