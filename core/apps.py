from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Infraestructura transversal: sin modelos propios de negocio."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "Núcleo del sistema"
