# ============================================================
# core/views.py — PORTADA PÚBLICA Y PANEL TRAS INICIAR SESIÓN
# "inicio" es la única pantalla, junto al login, que no exige
# sesión iniciada (regla de seguridad de la pauta). "panel" resume
# lo más relevante según el rol de quien inició sesión.
# ============================================================
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework.permissions import IsAuthenticated


def inicio(request):
    """Portada pública: explica el sistema sin exigir sesión."""
    return render(request, "core/inicio.html", {"titulo_pagina": "Inicio"})


@login_required
def panel(request):
    """Landing tras el login; el resumen depende del rol del usuario."""
    usuario = request.user
    contexto = {"titulo_pagina": "Mi panel"}

    if usuario.es_socio:
        from clases.models import EstadoReserva, Reserva
        from membresias.models import EstadoMembresia, Membresia

        socio = getattr(usuario, "socio", None)
        contexto["socio"] = socio
        if socio is not None:
            contexto["membresia"] = (
                Membresia.objects.filter(socio=socio, estado__in=[EstadoMembresia.ACTIVA, EstadoMembresia.CONGELADA])
                .select_related("plan")
                .first()
            )
            contexto["proximas_reservas"] = (
                Reserva.objects.filter(
                    socio=socio, estado__in=[EstadoReserva.CONFIRMADA, EstadoReserva.EN_ESPERA],
                    clase__inicio__gte=timezone.now(),
                )
                .select_related("clase__tipo")
                .order_by("clase__inicio")[:5]
            )

    elif usuario.es_instructor:
        from clases.models import Clase

        contexto["proximas_clases"] = (
            Clase.objects.filter(instructor=usuario, inicio__gte=timezone.now())
            .select_related("tipo")
            .order_by("inicio")[:5]
        )

    elif usuario.es_recepcion or usuario.es_administrador:
        from accesos.models import Instalacion
        from accesos.servicios import ocupacion_actual
        from clases.models import Clase
        from socios.models import Socio

        contexto["ocupacion_actual"] = ocupacion_actual()
        contexto["aforo_maximo"] = Instalacion.obtener().aforo_maximo
        contexto["total_socios"] = Socio.objects.count()
        contexto["clases_de_hoy"] = (
            Clase.objects.filter(inicio__date=timezone.localdate())
            .select_related("tipo", "instructor")
            .order_by("inicio")
        )

    return render(request, "core/panel.html", contexto)


# ============================================================
# DOCUMENTACIÓN DE LA API, PROTEGIDA CON SESIÓN INICIADA
# El esquema OpenAPI completo (rutas, modelos, hasta los nombres de
# los campos) no es información pública: exige autenticación igual
# que el resto de la API (sesión de staff o, si se usa fuera del
# navegador, un JWT válido).
# ============================================================
class SpectacularAPIViewProtegida(SpectacularAPIView):
    permission_classes = [IsAuthenticated]


class SpectacularSwaggerViewProtegida(SpectacularSwaggerView):
    permission_classes = [IsAuthenticated]


class SpectacularRedocViewProtegida(SpectacularRedocView):
    permission_classes = [IsAuthenticated]
