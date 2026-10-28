# ============================================================
# membresias/forms.py — PLANES, PAGOS Y CONGELAMIENTO (WEB)
# ============================================================
from django import forms

from socios.models import Socio

from .models import MetodoPago, Plan


class PlanForm(forms.ModelForm):
    class Meta:
        model = Plan
        fields = ["nombre", "descripcion", "precio", "duracion_dias", "clases_por_semana", "activo"]
        labels = {
            "nombre": "Nombre del plan",
            "descripcion": "Descripción",
            "precio": "Precio (CLP)",
            "duracion_dias": "Duración (días)",
            "clases_por_semana": "Clases grupales por semana",
            "activo": "Plan activo (disponible para vender)",
        }
        help_texts = {
            "clases_por_semana": "Vacío = sin límite de clases grupales por semana.",
        }
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control", "autofocus": True}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "precio": forms.NumberInput(attrs={"class": "form-control", "min": 1, "step": 1}),
            "duracion_dias": forms.NumberInput(attrs={"class": "form-control", "min": 1, "step": 1}),
            "clases_por_semana": forms.NumberInput(attrs={"class": "form-control", "min": 1, "step": 1}),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class RegistrarPagoForm(forms.Form):
    socio = forms.ModelChoiceField(
        label="Socio",
        queryset=Socio.objects.select_related("usuario").order_by("usuario__username"),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    plan = forms.ModelChoiceField(
        label="Plan",
        queryset=Plan.objects.filter(activo=True).order_by("precio"),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    monto = forms.IntegerField(
        label="Monto pagado (CLP)", min_value=1,
        help_text="Debe coincidir exactamente con el precio del plan.",
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )
    metodo = forms.ChoiceField(
        label="Método de pago", choices=MetodoPago.choices, widget=forms.Select(attrs={"class": "form-select"})
    )


class CongelarForm(forms.Form):
    dias = forms.IntegerField(
        label="Días a congelar", min_value=1, widget=forms.NumberInput(attrs={"class": "form-control"})
    )
