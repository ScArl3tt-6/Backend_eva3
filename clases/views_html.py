# ============================================================
# clases/views_html.py — CLASES Y RESERVAS (WEB)
# ============================================================
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from core.excepciones import ErrorDeNegocio
from core.utilidades import requiere_rol
from usuarios.models import Rol

from .forms import ClaseForm, TipoClaseForm
from .models import Clase, EstadoReserva, Reserva, TipoClase
from .servicios import cancelar_clase, cancelar_reserva, marcar_asistencia, reservar_clase


def _puede_ver_reserva(usuario, reserva) -> bool:
    if usuario.es_administrador or usuario.es_recepcion:
        return True
    if usuario.es_instructor:
        return reserva.clase.instructor_id == usuario.id
    return reserva.socio.usuario_id == usuario.id


# ============================================================
# TIPOS DE CLASE
# ============================================================
@requiere_rol(Rol.ADMINISTRADOR, Rol.RECEPCION)
def tipos_lista(request):
    tipos = TipoClase.objects.all().order_by("nombre")
    return render(request, "clases/tipos_lista.html", {"titulo_pagina": "Tipos de clase", "tipos": tipos})


@requiere_rol(Rol.ADMINISTRADOR, Rol.RECEPCION)
def tipo_crear(request):
    formulario = TipoClaseForm(request.POST or None)
    if request.method == "POST" and formulario.is_valid():
        formulario.save()
        messages.success(request, "Tipo de clase creado.")
        return redirect("tipos-clase-lista")
    return render(request, "parciales/formulario.html", {
        "titulo_pagina": "Nuevo tipo de clase", "formulario": formulario, "icono": "bi-tags",
        "url_cancelar": "/tipos-clase/", "texto_boton": "Crear",
    })


# ============================================================
# CLASES
# ============================================================
@login_required
def clases_lista(request):
    usuario = request.user
    clases = Clase.objects.select_related("tipo", "instructor").filter(
        inicio__gte=timezone.now() - timedelta(hours=3)
    ).order_by("inicio")

    if usuario.es_instructor:
        clases = clases.filter(instructor=usuario)

    clases = list(clases)
    if usuario.es_socio:
        socio = getattr(usuario, "socio", None)
        if socio is not None:
            reservas_propias = {
                r.clase_id: r
                for r in Reserva.objects.filter(socio=socio, estado__in=[EstadoReserva.CONFIRMADA, EstadoReserva.EN_ESPERA])
            }
            for clase in clases:
                clase.mi_reserva = reservas_propias.get(clase.id)

    return render(request, "clases/clases_lista.html", {"titulo_pagina": "Clases", "clases": clases})


@requiere_rol(Rol.ADMINISTRADOR, Rol.RECEPCION)
def clase_crear(request):
    formulario = ClaseForm(request.POST or None)
    if request.method == "POST" and formulario.is_valid():
        clase = formulario.save()
        messages.success(request, "Clase creada.")
        return redirect("clase-detalle", clase_id=clase.id)
    return render(request, "parciales/formulario.html", {
        "titulo_pagina": "Nueva clase", "formulario": formulario, "icono": "bi-calendar-plus",
        "url_cancelar": "/clases/", "texto_boton": "Crear clase",
    })


@requiere_rol(Rol.ADMINISTRADOR, Rol.RECEPCION)
def clase_editar(request, clase_id):
    clase = get_object_or_404(Clase, pk=clase_id)
    formulario = ClaseForm(request.POST or None, instance=clase)
    if request.method == "POST" and formulario.is_valid():
        formulario.save()
        messages.success(request, "Clase actualizada.")
        return redirect("clase-detalle", clase_id=clase.id)
    return render(request, "parciales/formulario.html", {
        "titulo_pagina": "Editar clase", "formulario": formulario, "icono": "bi-pencil-square",
        "url_cancelar": f"/clases/{clase.id}/", "texto_boton": "Guardar cambios",
    })


@login_required
def clase_detalle(request, clase_id):
    clase = get_object_or_404(Clase.objects.select_related("tipo", "instructor"), pk=clase_id)
    usuario = request.user
    if usuario.es_instructor and clase.instructor_id != usuario.id:
        raise PermissionDenied("Esta clase no está a tu cargo.")

    reservas = clase.reservas.select_related("socio__usuario").order_by("estado", "posicion_espera", "creada_en")
    reserva_propia = None
    if usuario.es_socio:
        socio = getattr(usuario, "socio", None)
        if socio is not None:
            reserva_propia = clase.reservas.filter(
                socio=socio, estado__in=[EstadoReserva.CONFIRMADA, EstadoReserva.EN_ESPERA]
            ).first()

    return render(request, "clases/clase_detalle.html", {
        "titulo_pagina": str(clase), "clase": clase, "reservas": reservas, "reserva_propia": reserva_propia,
    })


@requiere_rol(Rol.ADMINISTRADOR, Rol.RECEPCION)
def clase_cancelar(request, clase_id):
    clase = get_object_or_404(Clase, pk=clase_id)
    if request.method == "POST":
        cancelar_clase(clase, autor=request.user)
        messages.success(request, "Clase cancelada; sus reservas activas también se cancelaron.")
    return redirect("clase-detalle", clase_id=clase.id)


# ============================================================
# RESERVAS (SOCIO)
# ============================================================
@requiere_rol(Rol.SOCIO)
def reservar(request, clase_id):
    clase = get_object_or_404(Clase, pk=clase_id)
    socio = getattr(request.user, "socio", None)
    if request.method == "POST" and socio is not None:
        try:
            reserva = reservar_clase(socio, clase)
            if reserva.estado == EstadoReserva.CONFIRMADA:
                messages.success(request, "Reserva confirmada.")
            else:
                messages.warning(request, f"La clase está llena: quedaste en lista de espera, posición {reserva.posicion_espera}.")
        except ErrorDeNegocio as error:
            messages.error(request, error.mensaje)
    return redirect("clase-detalle", clase_id=clase.id)


@login_required
def mis_reservas(request):
    socio = getattr(request.user, "socio", None)
    if socio is None:
        raise PermissionDenied("Tu cuenta no tiene un perfil de socio.")
    reservas = Reserva.objects.filter(socio=socio).select_related("clase__tipo").order_by("-creada_en")
    return render(request, "clases/mis_reservas.html", {"titulo_pagina": "Mis reservas", "reservas": reservas})


@login_required
def cancelar_reserva_vista(request, reserva_id):
    reserva = get_object_or_404(Reserva.objects.select_related("clase", "socio"), pk=reserva_id)
    if not _puede_ver_reserva(request.user, reserva) or request.user.es_instructor:
        raise PermissionDenied("No puedes cancelar esta reserva.")
    if request.method == "POST":
        try:
            cancelar_reserva(reserva, autor=request.user)
            messages.success(request, "Reserva cancelada.")
        except ErrorDeNegocio as error:
            messages.error(request, error.mensaje)
    return redirect(request.POST.get("volver") or "mis-reservas")


# ============================================================
# ASISTENCIA (INSTRUCTOR)
# ============================================================
@requiere_rol(Rol.INSTRUCTOR)
def mis_clases(request):
    clases = Clase.objects.filter(instructor=request.user).order_by("-inicio")
    return render(request, "clases/mis_clases.html", {"titulo_pagina": "Mis clases", "clases": clases})


@requiere_rol(Rol.INSTRUCTOR)
def marcar_asistencia_vista(request, reserva_id):
    reserva = get_object_or_404(Reserva.objects.select_related("clase", "socio__usuario"), pk=reserva_id)
    if reserva.clase.instructor_id != request.user.id:
        raise PermissionDenied("Esta clase no está a tu cargo.")
    if request.method == "POST":
        asistio = request.POST.get("asistio") == "1"
        try:
            marcar_asistencia(reserva, asistio=asistio)
            messages.success(request, "Asistencia registrada.")
        except ErrorDeNegocio as error:
            messages.error(request, error.mensaje)
    return redirect("clase-detalle", clase_id=reserva.clase_id)
