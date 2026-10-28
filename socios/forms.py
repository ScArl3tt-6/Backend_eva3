# ============================================================
# socios/forms.py — ALTA Y EDICIÓN DE SOCIOS (WEB)
# SocioCrearForm crea el Usuario (rol SOCIO) y el Socio juntos: en
# la pantalla de recepción se registra una persona nueva de una
# sola vez, no en dos pasos separados.
# ============================================================
from django import forms
from django.contrib.auth.password_validation import validate_password

from usuarios.models import Rol, Usuario

from .models import Socio
from .validadores import formatear_rut, validar_rut


class SocioCrearForm(forms.Form):
    username = forms.CharField(
        label="Usuario", max_length=150, widget=forms.TextInput(attrs={"class": "form-control", "autofocus": True})
    )
    first_name = forms.CharField(label="Nombre", max_length=150, widget=forms.TextInput(attrs={"class": "form-control"}))
    last_name = forms.CharField(label="Apellido", max_length=150, widget=forms.TextInput(attrs={"class": "form-control"}))
    email = forms.EmailField(label="Correo electrónico", widget=forms.EmailInput(attrs={"class": "form-control"}))
    password = forms.CharField(
        label="Contraseña", widget=forms.PasswordInput(attrs={"class": "form-control"}),
        help_text="Mínimo 8 caracteres; no puede ser solo numérica ni demasiado común.",
    )
    rut = forms.CharField(
        label="RUT", max_length=12, validators=[validar_rut],
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "12345678-5"}),
    )
    telefono = forms.CharField(label="Teléfono", max_length=20, required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    contacto_emergencia_nombre = forms.CharField(
        label="Contacto de emergencia", max_length=150, required=False, widget=forms.TextInput(attrs={"class": "form-control"})
    )
    contacto_emergencia_telefono = forms.CharField(
        label="Teléfono de emergencia", max_length=20, required=False, widget=forms.TextInput(attrs={"class": "form-control"})
    )

    def clean_username(self):
        username = self.cleaned_data["username"]
        if Usuario.objects.filter(username=username).exists():
            raise forms.ValidationError("Ya existe un usuario con ese nombre.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"]
        if Usuario.objects.filter(email=email).exists():
            raise forms.ValidationError("Ya existe un usuario con ese correo electrónico.")
        return email

    def clean_password(self):
        password = self.cleaned_data["password"]
        validate_password(password)
        return password

    def clean_rut(self):
        rut = formatear_rut(self.cleaned_data["rut"])
        if Socio.objects.filter(rut=rut).exists():
            raise forms.ValidationError("Ya existe un socio con ese RUT.")
        return rut

    def guardar(self) -> Socio:
        datos = self.cleaned_data
        usuario = Usuario.objects.create_user(
            username=datos["username"],
            password=datos["password"],
            email=datos["email"],
            first_name=datos["first_name"],
            last_name=datos["last_name"],
            rol=Rol.SOCIO,
        )
        return Socio.objects.create(
            usuario=usuario,
            rut=datos["rut"],
            telefono=datos["telefono"],
            contacto_emergencia_nombre=datos["contacto_emergencia_nombre"],
            contacto_emergencia_telefono=datos["contacto_emergencia_telefono"],
        )


class SocioEditarForm(forms.ModelForm):
    class Meta:
        model = Socio
        fields = ["telefono", "contacto_emergencia_nombre", "contacto_emergencia_telefono"]
        labels = {
            "telefono": "Teléfono",
            "contacto_emergencia_nombre": "Contacto de emergencia",
            "contacto_emergencia_telefono": "Teléfono de emergencia",
        }
        widgets = {
            "telefono": forms.TextInput(attrs={"class": "form-control"}),
            "contacto_emergencia_nombre": forms.TextInput(attrs={"class": "form-control"}),
            "contacto_emergencia_telefono": forms.TextInput(attrs={"class": "form-control"}),
        }
