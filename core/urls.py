# ============================================================
# core/urls.py — RUTAS PÚBLICAS Y EL PANEL TRAS EL LOGIN
# ============================================================
from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("panel/", views.panel, name="panel"),
]
