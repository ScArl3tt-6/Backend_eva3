# ============================================================
# usuarios/urls.py — AUTENTICACIÓN (API Y WEB)
# "urlpatterns" es la API (se monta bajo /api/); "urlpatterns_html"
# es la sesión web. LogoutView solo acepta POST desde Django 4.1,
# que es justo lo que exige la pauta ("logout por POST").
# ============================================================
from django.contrib.auth import views as auth_views
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .forms import FormularioLogin
from .views import TokenObtenerParView

urlpatterns = [
    path("auth/token/", TokenObtenerParView.as_view(), name="token-obtener"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token-refrescar"),
]

urlpatterns_html = [
    path(
        "cuentas/login/",
        auth_views.LoginView.as_view(template_name="usuarios/login.html", authentication_form=FormularioLogin),
        name="login",
    ),
    path("cuentas/logout/", auth_views.LogoutView.as_view(), name="logout"),
]
