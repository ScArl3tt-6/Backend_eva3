# ============================================================
# clases/urls.py — RUTAS DE TIPOS DE CLASE, CLASES Y RESERVAS
# (API Y WEB)
# ============================================================
from django.urls import path
from rest_framework.routers import SimpleRouter

from . import views_html
from .views import ClaseViewSet, ReservaViewSet, TipoClaseViewSet

router = SimpleRouter()
router.register("tipos-clase", TipoClaseViewSet, basename="tipo-clase")
router.register("clases", ClaseViewSet, basename="clase")
router.register("reservas", ReservaViewSet, basename="reserva")

urlpatterns = router.urls

urlpatterns_html = [
    path("tipos-clase/", views_html.tipos_lista, name="tipos-clase-lista"),
    path("tipos-clase/nuevo/", views_html.tipo_crear, name="tipo-clase-crear"),
    path("clases/", views_html.clases_lista, name="clases-lista"),
    path("clases/nueva/", views_html.clase_crear, name="clase-crear"),
    path("clases/<int:clase_id>/", views_html.clase_detalle, name="clase-detalle"),
    path("clases/<int:clase_id>/editar/", views_html.clase_editar, name="clase-editar"),
    path("clases/<int:clase_id>/cancelar/", views_html.clase_cancelar, name="clase-cancelar-vista"),
    path("clases/<int:clase_id>/reservar/", views_html.reservar, name="clase-reservar"),
    path("mis-reservas/", views_html.mis_reservas, name="mis-reservas"),
    path("reservas/<int:reserva_id>/cancelar/", views_html.cancelar_reserva_vista, name="reserva-cancelar-vista"),
    path("mis-clases/", views_html.mis_clases, name="mis-clases"),
    path("reservas/<int:reserva_id>/asistencia/", views_html.marcar_asistencia_vista, name="reserva-asistencia-vista"),
]
