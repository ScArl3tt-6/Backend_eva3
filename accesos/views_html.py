# ============================================================
# accesos/views_html.py — VALIDACIÓN DE ACCESO Y AFORO (WEB)
# El dashboard de aforo (accesos/aforo.html) no trae datos desde
# esta vista: solo renderiza la pantalla; los números llegan por
# fetch cada 5s a GET /api/aforo/ (ver BLOQUE 4 de la pauta).
# ============================================================
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, render

from core.excepciones import ErrorDeNegocio
from core.utilidades import requiere_rol
from socios.models import Socio
from usuarios.models import Rol

from .models import RegistroAcceso, TipoAcceso
from .servicios import validar_acceso


def _puede_ver_socio(usuario, socio) -> bool:
    return usuario.es_administrador or usuario.es_recepcion or socio.usuario_id == usuario.id


@requiere_rol(Rol.ADMINISTRADOR, Rol.RECEPCION)
def validar_pantalla(request):
    resultado = None
    if request.method == "POST":
        token = request.POST.get("token", "").strip()
        tipo = request.POST.get("tipo", TipoAcceso.ENTRADA)
        try:
            resultado = validar_acceso(token=token, tipo=tipo, registrado_por=request.user)
        except ErrorDeNegocio as error:
            messages.error(request, error.mensaje)

    ultimos = RegistroAcceso.objects.select_related("socio__usuario").order_by("-fecha_hora")[:15]
    return render(request, "accesos/validar.html", {
        "titulo_pagina": "Validar acceso", "resultado": resultado, "ultimos": ultimos,
    })


@login_required
def mi_historial(request):
    socio = getattr(request.user, "socio", None)
    if socio is None:
        raise PermissionDenied("Tu cuenta no tiene un perfil de socio.")
    accesos = RegistroAcceso.objects.filter(socio=socio).order_by("-fecha_hora")
    return render(request, "accesos/historial.html", {
        "titulo_pagina": "Mi historial de accesos", "accesos": accesos,
    })


@login_required
def accesos_de_socio(request, socio_id):
    socio = get_object_or_404(Socio, pk=socio_id)
    if not _puede_ver_socio(request.user, socio):
        raise PermissionDenied("No puedes ver los accesos de otro socio.")
    accesos = RegistroAcceso.objects.filter(socio=socio).order_by("-fecha_hora")
    return render(request, "accesos/historial.html", {
        "titulo_pagina": f"Accesos de {socio}", "accesos": accesos,
    })


@requiere_rol(Rol.ADMINISTRADOR, Rol.RECEPCION)
def aforo_dashboard(request):
    return render(request, "accesos/aforo.html", {"titulo_pagina": "Aforo en tiempo real"})
