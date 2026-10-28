# ============================================================
# membresias/urls.py — RUTAS DE PLANES, MEMBRESÍAS Y PAGOS (API Y WEB)
# ============================================================
from django.urls import path
from rest_framework.routers import SimpleRouter

from . import views_html
from .views import MembresiaViewSet, PagoViewSet, PlanViewSet

router = SimpleRouter()
router.register("planes", PlanViewSet, basename="plan")
router.register("membresias", MembresiaViewSet, basename="membresia")
router.register("pagos", PagoViewSet, basename="pago")

urlpatterns = router.urls

urlpatterns_html = [
    path("planes/", views_html.planes_lista, name="planes-lista"),
    path("planes/nuevo/", views_html.plan_crear, name="plan-crear"),
    path("planes/<int:plan_id>/editar/", views_html.plan_editar, name="plan-editar"),
    path("membresias/", views_html.membresias_lista, name="membresias-lista"),
    path("membresias/<int:membresia_id>/", views_html.membresia_detalle, name="membresia-detalle"),
    path("membresias/<int:membresia_id>/congelar/", views_html.membresia_congelar, name="membresia-congelar"),
    path("membresias/<int:membresia_id>/descongelar/", views_html.membresia_descongelar, name="membresia-descongelar"),
    path("socios/<int:socio_id>/membresias/", views_html.membresias_de_socio, name="membresias-de-socio"),
    path("pagos/", views_html.pagos_lista, name="pagos-lista"),
    path("pagos/nuevo/", views_html.pago_crear, name="pago-crear"),
]
