from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Infraestructura transversal: sin modelos propios de negocio."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "Núcleo del sistema"

    def ready(self):
        """Pone la marca FitLife en el Django Admin (encabezado y títulos en español)."""
        from django.conf import settings
        from django.contrib import admin

        admin.site.site_header = f"{settings.NOMBRE_COMERCIAL} — Administración"
        admin.site.site_title = settings.NOMBRE_COMERCIAL
        admin.site.index_title = "Panel de administración"
