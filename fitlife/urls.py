# ============================================================
# fitlife/urls.py — RUTEO RAÍZ DEL PROYECTO
# Cada app expone dos listas en su urls.py:
#   urlpatterns       → API REST, se monta bajo /api/
#   urlpatterns_html  → pantallas HTML, se montan en la raíz
# ============================================================
from django.contrib import admin
from django.urls import include, path

from accesos import urls as accesos_urls
from clases import urls as clases_urls
from core import urls as core_urls
from core.views import SpectacularAPIViewProtegida, SpectacularRedocViewProtegida, SpectacularSwaggerViewProtegida
from membresias import urls as membresias_urls
from socios import urls as socios_urls
from usuarios import urls as usuarios_urls

# ============================================================
# BLOQUE 1 — RUTAS DE LA API REST (se unen bajo el namespace "api")
# ============================================================
rutas_api = (
    usuarios_urls.urlpatterns
    + socios_urls.urlpatterns
    + membresias_urls.urlpatterns
    + accesos_urls.urlpatterns
    + clases_urls.urlpatterns
)

# ============================================================
# BLOQUE 2 — RUTAS DE LAS PANTALLAS HTML (se montan en la raíz)
# ============================================================
rutas_html = (
    socios_urls.urlpatterns_html
    + membresias_urls.urlpatterns_html
    + accesos_urls.urlpatterns_html
    + clases_urls.urlpatterns_html
)

urlpatterns = [
    # --- Documentación OpenAPI 3 (exige sesión iniciada: no es información pública) ---
    path("api/schema/", SpectacularAPIViewProtegida.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerViewProtegida.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocViewProtegida.as_view(url_name="schema"), name="redoc"),
    # --- API REST ---
    path("api/", include((rutas_api, "api"))),
    # --- Django Admin ---
    path("admin/", admin.site.urls),
    # --- Pantallas HTML ---
    *rutas_html,
    path("", include((usuarios_urls.urlpatterns_html, "usuarios"))),
    path("", include("core.urls")),
]
