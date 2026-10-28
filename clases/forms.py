# ============================================================
# clases/forms.py — TIPOS DE CLASE Y CLASES (WEB)
# ============================================================
from django import forms

from usuarios.models import Rol, Usuario

from .models import Clase, TipoClase


class TipoClaseForm(forms.ModelForm):
    class Meta:
        model = TipoClase
        fields = ["nombre", "descripcion"]
        labels = {"nombre": "Nombre", "descripcion": "Descripción"}
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control", "autofocus": True}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class ClaseForm(forms.ModelForm):
    class Meta:
        model = Clase
        fields = ["tipo", "instructor", "sala", "inicio", "fin", "cupo_maximo"]
        labels = {
            "tipo": "Tipo de clase",
            "instructor": "Instructor",
            "sala": "Sala",
            "inicio": "Inicio",
            "fin": "Término",
            "cupo_maximo": "Cupo máximo",
        }
        widgets = {
            "tipo": forms.Select(attrs={"class": "form-select"}),
            "instructor": forms.Select(attrs={"class": "form-select"}),
            "sala": forms.TextInput(attrs={"class": "form-control"}),
            "inicio": forms.DateTimeInput(attrs={"class": "form-control", "type": "datetime-local"}),
            "fin": forms.DateTimeInput(attrs={"class": "form-control", "type": "datetime-local"}),
            "cupo_maximo": forms.NumberInput(attrs={"class": "form-control", "min": 1, "step": 1}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["instructor"].queryset = Usuario.objects.filter(rol=Rol.INSTRUCTOR).order_by("username")
        self.fields["inicio"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["fin"].input_formats = ["%Y-%m-%dT%H:%M"]

    def clean(self):
        datos = super().clean()
        inicio, fin = datos.get("inicio"), datos.get("fin")
        if inicio and fin and fin <= inicio:
            raise forms.ValidationError("El término debe ser posterior al inicio.")
        return datos
