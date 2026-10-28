# ============================================================
# socios/urls.py — RUTAS DE SOCIOS (API Y WEB)
# Los nombres de las rutas web van prefijados con "socio-" porque
# se montan en una lista plana junto con las de las demás apps (sin
# namespace), igual que en el resto del proyecto.
# ============================================================
from django.urls import path
from rest_framework.routers import SimpleRouter

from . import views_html
from .views import SocioViewSet

router = SimpleRouter()
router.register("socios", SocioViewSet, basename="socio")

urlpatterns = router.urls

urlpatterns_html = [
    path("mi-qr/", views_html.mi_qr, name="socio-mi-qr"),
    path("mi-qr/regenerar/", views_html.regenerar_qr, name="socio-mi-qr-regenerar"),
    path("socios/", views_html.socios_lista, name="socios-lista"),
    path("socios/nuevo/", views_html.socio_crear, name="socio-crear"),
    path("socios/<int:socio_id>/", views_html.socio_detalle, name="socio-detalle"),
    path("socios/<int:socio_id>/editar/", views_html.socio_editar, name="socio-editar"),
    path("socios/<int:socio_id>/qr.svg", views_html.qr_svg, name="socio-qr-svg"),
]
