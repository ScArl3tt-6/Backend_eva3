# ============================================================
# core/nombres.py — NOMBRES DE LAS VISTAS EN LA API NAVEGABLE
# Responsabilidad: que la Browsable API de DRF muestre títulos en
# español correcto en vez del nombre de la clase Python (p. ej.
# "SocioViewSet" se vería como «Socio List» sin esto).
#
# Se registra en REST_FRAMEWORK["VIEW_NAME_FUNCTION"]. Cada app
# agrega aquí sus vistas a medida que se crean; si una clase no está
# en el diccionario, se usa el comportamiento estándar de DRF, de
# modo que nada se rompe al agregar una vista nueva.
# ============================================================

from rest_framework.views import get_view_name as nombre_por_omision

NOMBRES_DE_VISTA = {
    # Se completa en cada fase a medida que se crean las vistas de la API.
}

SUFIJOS = {
    "List": "listado",
    "Instance": "detalle",
}


def nombre_de_vista(view) -> str:
    """Devuelve el título en español de una vista de la API navegable."""
    nombre = NOMBRES_DE_VISTA.get(view.__class__.__name__)

    if nombre is None:
        return nombre_por_omision(view)

    sufijo = getattr(view, "suffix", None)
    if sufijo:
        return f"{nombre} · {SUFIJOS.get(sufijo, sufijo.lower())}"

    return nombre
