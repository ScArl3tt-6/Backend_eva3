# ============================================================
# socios/views_html.py — PANTALLAS WEB DE SOCIOS
# Responsabilidad: perfil y QR del propio socio, y el CRUD de
# socios para recepción/administración. El control de acceso a
# nivel de objeto se repite aquí (además de en la API): un socio
# jamás ve el perfil ni el QR de otro socio.
# ============================================================
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render

from accesos.qr import generar_qr_svg
from core.utilidades import requiere_rol
from usuarios.models import Rol

from .forms import SocioCrearForm, SocioEditarForm
from .models import Socio


def _puede_ver_socio(usuario, socio) -> bool:
    return usuario.es_administrador or usuario.es_recepcion or socio.usuario_id == usuario.id


@login_required
def mi_qr(request):
    socio = getattr(request.user, "socio", None)
    if socio is None:
        raise PermissionDenied("Tu cuenta no tiene un perfil de socio.")
    return render(request, "socios/mi_qr.html", {"titulo_pagina": "Mi código QR", "socio": socio})


@login_required
def qr_svg(request, socio_id):
    socio = get_object_or_404(Socio, pk=socio_id)
    if not _puede_ver_socio(request.user, socio):
        raise PermissionDenied("No puedes ver el código QR de otro socio.")
    return HttpResponse(generar_qr_svg(socio.token_qr), content_type="image/svg+xml")


@login_required
def regenerar_qr(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    socio = getattr(request.user, "socio", None)
    if socio is None:
        raise PermissionDenied("Tu cuenta no tiene un perfil de socio.")

    socio.regenerar_token_qr()
    messages.success(request, "Tu código QR fue regenerado: el anterior ya no sirve para ingresar.")
    return redirect("socio-mi-qr")


@requiere_rol(Rol.ADMINISTRADOR, Rol.RECEPCION)
def socios_lista(request):
    busqueda = request.GET.get("q", "").strip()
    socios = Socio.objects.select_related("usuario").order_by("usuario__username")
    if busqueda:
        socios = socios.filter(rut__icontains=busqueda) | socios.filter(usuario__username__icontains=busqueda)
    return render(request, "socios/lista.html", {"titulo_pagina": "Socios", "socios": socios, "busqueda": busqueda})


@requiere_rol(Rol.ADMINISTRADOR, Rol.RECEPCION)
def socio_crear(request):
    formulario = SocioCrearForm(request.POST or None)
    if request.method == "POST" and formulario.is_valid():
        socio = formulario.guardar()
        messages.success(request, f"Socio «{socio}» registrado correctamente.")
        return redirect("socio-detalle", socio_id=socio.id)

    return render(request, "parciales/formulario.html", {
        "titulo_pagina": "Nuevo socio",
        "formulario": formulario,
        "icono": "bi-person-plus",
        "url_cancelar": "/socios/",
        "texto_boton": "Registrar socio",
    })


@login_required
def socio_detalle(request, socio_id):
    socio = get_object_or_404(Socio.objects.select_related("usuario"), pk=socio_id)
    if not _puede_ver_socio(request.user, socio):
        raise PermissionDenied("No puedes ver el perfil de otro socio.")
    return render(request, "socios/detalle.html", {"titulo_pagina": str(socio), "socio": socio})


@requiere_rol(Rol.ADMINISTRADOR, Rol.RECEPCION)
def socio_editar(request, socio_id):
    socio = get_object_or_404(Socio, pk=socio_id)
    formulario = SocioEditarForm(request.POST or None, instance=socio)
    if request.method == "POST" and formulario.is_valid():
        formulario.save()
        messages.success(request, "Datos del socio actualizados.")
        return redirect("socio-detalle", socio_id=socio.id)

    return render(request, "parciales/formulario.html", {
        "titulo_pagina": f"Editar a {socio}",
        "formulario": formulario,
        "icono": "bi-pencil-square",
        "url_cancelar": f"/socios/{socio.id}/",
        "texto_boton": "Guardar cambios",
    })
