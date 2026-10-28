# ============================================================
# membresias/views_html.py — PLANES, MEMBRESÍAS Y PAGOS (WEB)
# Las reglas de negocio se llaman tal cual de servicios.py; esta
# capa solo valida el formulario y traduce ErrorDeNegocio a un
# mensaje flash, igual que lo hace core.excepciones con la API.
# ============================================================
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from core.excepciones import ErrorDeNegocio
from core.utilidades import requiere_rol
from socios.models import Socio
from usuarios.models import Rol

from .forms import CongelarForm, PlanForm, RegistrarPagoForm
from .models import Membresia, Pago, Plan
from .servicios import congelar, descongelar, registrar_pago


def _puede_ver_socio(usuario, socio) -> bool:
    return usuario.es_administrador or usuario.es_recepcion or socio.usuario_id == usuario.id


# ============================================================
# PLANES (solo administrador)
# ============================================================
@requiere_rol(Rol.ADMINISTRADOR)
def planes_lista(request):
    planes = Plan.objects.all().order_by("precio")
    return render(request, "membresias/planes_lista.html", {"titulo_pagina": "Planes", "planes": planes})


@requiere_rol(Rol.ADMINISTRADOR)
def plan_crear(request):
    formulario = PlanForm(request.POST or None)
    if request.method == "POST" and formulario.is_valid():
        formulario.save()
        messages.success(request, "Plan creado correctamente.")
        return redirect("planes-lista")
    return render(request, "parciales/formulario.html", {
        "titulo_pagina": "Nuevo plan", "formulario": formulario, "icono": "bi-card-list",
        "url_cancelar": "/planes/", "texto_boton": "Crear plan",
    })


@requiere_rol(Rol.ADMINISTRADOR)
def plan_editar(request, plan_id):
    plan = get_object_or_404(Plan, pk=plan_id)
    formulario = PlanForm(request.POST or None, instance=plan)
    if request.method == "POST" and formulario.is_valid():
        formulario.save()
        messages.success(request, "Plan actualizado.")
        return redirect("planes-lista")
    return render(request, "parciales/formulario.html", {
        "titulo_pagina": f"Editar {plan.nombre}", "formulario": formulario, "icono": "bi-pencil-square",
        "url_cancelar": "/planes/", "texto_boton": "Guardar cambios",
    })


# ============================================================
# MEMBRESÍAS
# ============================================================
def _membresias_visibles(usuario):
    qs = Membresia.objects.select_related("socio__usuario", "plan")
    if usuario.es_administrador or usuario.es_recepcion:
        return qs
    socio = getattr(usuario, "socio", None)
    return qs.filter(socio=socio) if socio else qs.none()


@login_required
def membresias_lista(request):
    membresias = _membresias_visibles(request.user).order_by("-fecha_inicio")
    return render(request, "membresias/membresias_lista.html", {"titulo_pagina": "Membresías", "membresias": membresias})


@login_required
def membresias_de_socio(request, socio_id):
    socio = get_object_or_404(Socio, pk=socio_id)
    if not _puede_ver_socio(request.user, socio):
        raise PermissionDenied("No puedes ver las membresías de otro socio.")

    membresias = Membresia.objects.filter(socio=socio).select_related("plan").order_by("-fecha_inicio")
    pagos = Pago.objects.filter(socio=socio).select_related("plan").order_by("-fecha")
    return render(request, "membresias/membresias_de_socio.html", {
        "titulo_pagina": f"Membresías de {socio}", "socio": socio, "membresias": membresias, "pagos": pagos,
    })


@login_required
def membresia_detalle(request, membresia_id):
    membresia = get_object_or_404(Membresia.objects.select_related("socio__usuario", "plan"), pk=membresia_id)
    if not _puede_ver_socio(request.user, membresia.socio):
        raise PermissionDenied("No puedes ver la membresía de otro socio.")

    return render(request, "membresias/membresia_detalle.html", {
        "titulo_pagina": "Detalle de membresía",
        "membresia": membresia,
        "historial": membresia.historial.all(),
        "congelar_form": CongelarForm(),
    })


@requiere_rol(Rol.ADMINISTRADOR, Rol.RECEPCION)
def membresia_congelar(request, membresia_id):
    membresia = get_object_or_404(Membresia, pk=membresia_id)
    if request.method == "POST":
        formulario = CongelarForm(request.POST)
        if formulario.is_valid():
            try:
                congelar(membresia, dias=formulario.cleaned_data["dias"], autor=request.user)
                messages.success(request, "Membresía congelada.")
            except ErrorDeNegocio as error:
                messages.error(request, error.mensaje)
        else:
            messages.error(request, "Ingrese una cantidad de días válida.")
    return redirect("membresia-detalle", membresia_id=membresia.id)


@requiere_rol(Rol.ADMINISTRADOR, Rol.RECEPCION)
def membresia_descongelar(request, membresia_id):
    membresia = get_object_or_404(Membresia, pk=membresia_id)
    if request.method == "POST":
        try:
            descongelar(membresia, autor=request.user)
            messages.success(request, "Membresía descongelada: se extendió la fecha de término.")
        except ErrorDeNegocio as error:
            messages.error(request, error.mensaje)
    return redirect("membresia-detalle", membresia_id=membresia.id)


# ============================================================
# PAGOS
# ============================================================
@requiere_rol(Rol.ADMINISTRADOR, Rol.RECEPCION)
def pagos_lista(request):
    pagos = Pago.objects.select_related("socio__usuario", "plan").order_by("-fecha")
    return render(request, "membresias/pagos_lista.html", {"titulo_pagina": "Pagos", "pagos": pagos})


@requiere_rol(Rol.ADMINISTRADOR, Rol.RECEPCION)
def pago_crear(request):
    formulario = RegistrarPagoForm(request.POST or None)
    if request.method == "POST" and formulario.is_valid():
        try:
            pago = registrar_pago(
                socio=formulario.cleaned_data["socio"],
                plan=formulario.cleaned_data["plan"],
                monto=formulario.cleaned_data["monto"],
                metodo=formulario.cleaned_data["metodo"],
                registrado_por=request.user,
            )
            messages.success(request, f"Pago {pago.comprobante} registrado: membresía activada o renovada.")
            return redirect("membresia-detalle", membresia_id=pago.membresia_id)
        except ErrorDeNegocio as error:
            messages.error(request, error.mensaje)

    return render(request, "parciales/formulario.html", {
        "titulo_pagina": "Registrar pago", "formulario": formulario, "icono": "bi-cash-coin",
        "url_cancelar": "/pagos/", "texto_boton": "Registrar pago",
    })
