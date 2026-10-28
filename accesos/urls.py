# ============================================================
# accesos/urls.py — RUTAS DE ACCESOS Y AFORO (API Y WEB)
# ============================================================
from django.urls import path
from rest_framework.routers import SimpleRouter

from . import views_html
from .views import AforoView, RegistroAccesoViewSet, ValidarAccesoView

router = SimpleRouter()
router.register("accesos", RegistroAccesoViewSet, basename="acceso")

# "accesos/validar/" va ANTES de router.urls: si no, el patrón de detalle
# del router (accesos/<pk>/) coincide primero y toma "validar" como pk,
# devolviendo 405 en vez de ejecutar ValidarAccesoView.
urlpatterns = [
    path("accesos/validar/", ValidarAccesoView.as_view(), name="acceso-validar"),
    path("aforo/", AforoView.as_view(), name="aforo"),
] + router.urls

urlpatterns_html = [
    path("accesos/validar/", views_html.validar_pantalla, name="acceso-validar-pantalla"),
    path("mis-accesos/", views_html.mi_historial, name="acceso-mi-historial"),
    path("socios/<int:socio_id>/accesos/", views_html.accesos_de_socio, name="accesos-de-socio"),
    path("aforo/", views_html.aforo_dashboard, name="aforo-dashboard"),
]
