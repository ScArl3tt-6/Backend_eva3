# ============================================================
# core/context_processors.py — DATOS DISPONIBLES EN TODAS LAS PLANTILLAS
# Responsabilidad: inyectar el nombre de la alumna y el nombre
# comercial del gimnasio (ambos desde .env) sin repetirlos en cada
# vista. El footer y la cabecera los leen directamente del contexto.
# ============================================================

from django.conf import settings


def datos_alumno(request):
    """Expone ALUMNO_NOMBRE y NOMBRE_COMERCIAL a cualquier plantilla."""
    return {
        "alumno_nombre": settings.ALUMNO_NOMBRE,
        "nombre_comercial": settings.NOMBRE_COMERCIAL,
    }
