# ============================================================
# usuarios/forms.py — FORMULARIO DE LOGIN CON ESTILO PROPIO
# AuthenticationForm no agrega clases CSS a sus campos; se
# sobrescriben los widgets para que se vean como el resto de los
# formularios del sitio (clase .form-control de tema.css).
# ============================================================
from django import forms
from django.contrib.auth.forms import AuthenticationForm


class FormularioLogin(AuthenticationForm):
    """Login con los mismos estilos de formulario que el resto del sitio."""

    username = forms.CharField(
        label="Usuario",
        widget=forms.TextInput(attrs={"class": "form-control", "autofocus": True}),
    )
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )
