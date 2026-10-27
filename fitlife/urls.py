# ============================================================
# fitlife/urls.py — RUTEO RAÍZ DEL PROYECTO
# Cada fase agrega su propio include() a medida que se crean las
# apps (usuarios, socios, membresias, accesos, clases) y el router
# de la API bajo /api/.
# ============================================================
from django.contrib import admin
from django.urls import path

urlpatterns = [
    path("admin/", admin.site.urls),
]
