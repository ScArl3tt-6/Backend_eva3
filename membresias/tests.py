# ============================================================
# membresias/tests.py — PAGOS, ACTIVACIÓN/RENOVACIÓN Y ESTADOS
# ============================================================
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from socios.models import Socio
from usuarios.models import Rol, Usuario

from .models import EstadoMembresia, Membresia, MetodoPago, Pago, Plan
from .servicios import (
    MembresiaCongeladaError,
    MontoInvalidoError,
    RangoDeCongelamientoError,
    TransicionInvalidaError,
    actualizar_membresias_vencidas,
    congelar,
    descongelar,
    registrar_pago,
    verificar_vencimiento,
)


def _crear_socio(username):
    usuario = Usuario.objects.create_user(
        username=username, password="Clave.2026", rol=Rol.SOCIO, email=f"{username}@fitlife.cl"
    )
    # RUT válido distinto por socio: se reutiliza el cuerpo de prueba 11111111
    # con un dígito del username para no colisionar la unicidad.
    sufijo = str(abs(hash(username)) % 9000000 + 1000000)
    from socios.validadores import calcular_dv

    rut = f"{sufijo}-{calcular_dv(sufijo)}"
    return Socio.objects.create(usuario=usuario, rut=rut)


def _crear_plan(nombre="Plan Mensual", precio=29990, duracion_dias=30):
    return Plan.objects.create(nombre=nombre, precio=precio, duracion_dias=duracion_dias)


class RegistrarPagoTests(TestCase):
    """Los tres casos de registrar_pago exigidos por la pauta."""

    def setUp(self):
        self.socio = _crear_socio("socio_pago1")
        self.plan = _crear_plan()

    def test_monto_distinto_al_precio_del_plan_es_rechazado(self):
        with self.assertRaises(MontoInvalidoError):
            registrar_pago(socio=self.socio, plan=self.plan, monto=self.plan.precio - 1, metodo=MetodoPago.EFECTIVO)
        self.assertEqual(Membresia.objects.filter(socio=self.socio).count(), 0)

    def test_caso_sin_membresia_previa_crea_una_nueva_desde_hoy(self):
        pago = registrar_pago(socio=self.socio, plan=self.plan, monto=self.plan.precio, metodo=MetodoPago.EFECTIVO)

        membresia = pago.membresia
        hoy = timezone.localdate()
        self.assertEqual(membresia.estado, EstadoMembresia.ACTIVA)
        self.assertEqual(membresia.fecha_inicio, hoy)
        self.assertEqual(membresia.fecha_fin, hoy + timedelta(days=self.plan.duracion_dias))

    def test_caso_membresia_activa_vigente_extiende_fecha_fin(self):
        primer_pago = registrar_pago(
            socio=self.socio, plan=self.plan, monto=self.plan.precio, metodo=MetodoPago.EFECTIVO
        )
        fecha_fin_original = primer_pago.membresia.fecha_fin

        segundo_pago = registrar_pago(
            socio=self.socio, plan=self.plan, monto=self.plan.precio, metodo=MetodoPago.TRANSFERENCIA
        )

        self.assertEqual(segundo_pago.membresia_id, primer_pago.membresia_id)  # misma fila, renovada
        self.assertEqual(
            segundo_pago.membresia.fecha_fin, fecha_fin_original + timedelta(days=self.plan.duracion_dias)
        )

    def test_caso_membresia_congelada_rechaza_el_pago(self):
        pago = registrar_pago(socio=self.socio, plan=self.plan, monto=self.plan.precio, metodo=MetodoPago.EFECTIVO)
        congelar(pago.membresia, dias=10)

        with self.assertRaises(MembresiaCongeladaError):
            registrar_pago(socio=self.socio, plan=self.plan, monto=self.plan.precio, metodo=MetodoPago.EFECTIVO)

    def test_membresia_vencida_no_se_reutiliza_se_crea_una_nueva(self):
        hoy = timezone.localdate()
        vencida = Membresia.objects.create(
            socio=self.socio,
            plan=self.plan,
            fecha_inicio=hoy - timedelta(days=60),
            fecha_fin=hoy - timedelta(days=5),
            estado=EstadoMembresia.ACTIVA,  # se marcará VENCIDA en tiempo real al pagar
        )

        pago = registrar_pago(socio=self.socio, plan=self.plan, monto=self.plan.precio, metodo=MetodoPago.EFECTIVO)

        vencida.refresh_from_db()
        self.assertEqual(vencida.estado, EstadoMembresia.VENCIDA)
        self.assertNotEqual(pago.membresia_id, vencida.id)
        self.assertEqual(pago.membresia.fecha_inicio, hoy)


class CongelarDescongelarTests(TestCase):
    def setUp(self):
        self.socio = _crear_socio("socio_frz1")
        self.plan = _crear_plan()
        self.membresia = Membresia.objects.create(
            socio=self.socio,
            plan=self.plan,
            fecha_inicio=timezone.localdate(),
            fecha_fin=timezone.localdate() + timedelta(days=30),
            estado=EstadoMembresia.ACTIVA,
        )

    def test_congelar_cambia_estado_y_guarda_dias(self):
        congelar(self.membresia, dias=10)
        self.membresia.refresh_from_db()
        self.assertEqual(self.membresia.estado, EstadoMembresia.CONGELADA)
        self.assertEqual(self.membresia.dias_congelados, 10)

    def test_congelar_fuera_del_rango_configurado_es_rechazado(self):
        with self.assertRaises(RangoDeCongelamientoError):
            congelar(self.membresia, dias=1)  # bajo CONGELAMIENTO_DIAS_MIN
        with self.assertRaises(RangoDeCongelamientoError):
            congelar(self.membresia, dias=9999)  # sobre CONGELAMIENTO_DIAS_MAX

    def test_congelar_una_membresia_vencida_es_rechazado(self):
        self.membresia.estado = EstadoMembresia.VENCIDA
        self.membresia.save(update_fields=["estado"])
        with self.assertRaises(TransicionInvalidaError):
            congelar(self.membresia, dias=10)

    def test_descongelar_extiende_fecha_fin_por_los_dias_congelados(self):
        congelar(self.membresia, dias=15)
        fecha_fin_congelada = self.membresia.fecha_fin

        descongelar(self.membresia)

        self.membresia.refresh_from_db()
        self.assertEqual(self.membresia.estado, EstadoMembresia.ACTIVA)
        self.assertEqual(self.membresia.fecha_fin, fecha_fin_congelada + timedelta(days=15))

    def test_descongelar_una_membresia_activa_es_rechazado(self):
        with self.assertRaises(TransicionInvalidaError):
            descongelar(self.membresia)


class VencimientoTests(TestCase):
    def setUp(self):
        self.socio = _crear_socio("socio_venc1")
        self.plan = _crear_plan()

    def test_verificar_vencimiento_marca_vencida_en_tiempo_real(self):
        membresia = Membresia.objects.create(
            socio=self.socio,
            plan=self.plan,
            fecha_inicio=timezone.localdate() - timedelta(days=40),
            fecha_fin=timezone.localdate() - timedelta(days=1),
            estado=EstadoMembresia.ACTIVA,
        )
        verificar_vencimiento(membresia)
        membresia.refresh_from_db()
        self.assertEqual(membresia.estado, EstadoMembresia.VENCIDA)

    def test_actualizar_membresias_vencidas_es_idempotente(self):
        Membresia.objects.create(
            socio=self.socio,
            plan=self.plan,
            fecha_inicio=timezone.localdate() - timedelta(days=40),
            fecha_fin=timezone.localdate() - timedelta(days=1),
            estado=EstadoMembresia.ACTIVA,
        )

        primera_pasada = actualizar_membresias_vencidas()
        segunda_pasada = actualizar_membresias_vencidas()

        self.assertEqual(primera_pasada, 1)
        self.assertEqual(segunda_pasada, 0)  # ya no queda ninguna ACTIVA vencida por procesar

    def test_congelada_no_vence_aunque_pase_la_fecha_fin(self):
        membresia = Membresia.objects.create(
            socio=self.socio,
            plan=self.plan,
            fecha_inicio=timezone.localdate() - timedelta(days=40),
            fecha_fin=timezone.localdate() - timedelta(days=1),
            estado=EstadoMembresia.CONGELADA,
            dias_congelados=10,
        )
        actualizar_membresias_vencidas()
        membresia.refresh_from_db()
        self.assertEqual(membresia.estado, EstadoMembresia.CONGELADA)


class RestriccionesDeBaseDeDatosTests(TestCase):
    def test_no_puede_haber_dos_membresias_activas_o_congeladas_a_la_vez(self):
        socio = _crear_socio("socio_unica1")
        plan = _crear_plan()
        Membresia.objects.create(
            socio=socio, plan=plan, fecha_inicio=timezone.localdate(),
            fecha_fin=timezone.localdate() + timedelta(days=30), estado=EstadoMembresia.ACTIVA,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Membresia.objects.create(
                    socio=socio, plan=plan, fecha_inicio=timezone.localdate(),
                    fecha_fin=timezone.localdate() + timedelta(days=30), estado=EstadoMembresia.CONGELADA,
                )

    def test_plan_con_precio_cero_es_rechazado_por_la_base_de_datos(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Plan.objects.create(nombre="Plan inválido", precio=0, duracion_dias=30)

    def test_pago_con_monto_cero_es_rechazado_por_la_base_de_datos(self):
        socio = _crear_socio("socio_montocero")
        plan = _crear_plan(nombre="Plan B", precio=10000)
        membresia = Membresia.objects.create(
            socio=socio, plan=plan, fecha_inicio=timezone.localdate(),
            fecha_fin=timezone.localdate() + timedelta(days=30), estado=EstadoMembresia.ACTIVA,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Pago.objects.create(
                    socio=socio, plan=plan, membresia=membresia, monto=0, metodo=MetodoPago.EFECTIVO
                )


class ControlDeAccesoDeObjetoApiTests(TestCase):
    """Un socio jamás debe ver los pagos ni las membresías de otro socio vía API."""

    def setUp(self):
        self.cliente = APIClient()
        self.socio1 = _crear_socio("socio_pago_api1")
        self.socio2 = _crear_socio("socio_pago_api2")

    def _pagar(self, socio, nombre_plan):
        plan = _crear_plan(nombre=nombre_plan)
        return registrar_pago(socio=socio, plan=plan, monto=plan.precio, metodo=MetodoPago.EFECTIVO)

    def test_un_socio_no_ve_los_pagos_de_otro_socio_en_la_lista(self):
        pago_propio = self._pagar(self.socio2, "Plan API 1")
        self._pagar(self.socio1, "Plan API 2")

        self.cliente.force_authenticate(user=self.socio2.usuario)
        respuesta = self.cliente.get("/api/pagos/")
        ids_devueltos = [fila["id"] for fila in respuesta.data["results"]]
        self.assertEqual(ids_devueltos, [pago_propio.id])

    def test_un_socio_no_puede_obtener_el_detalle_del_pago_de_otro_por_id(self):
        pago_de_otro = self._pagar(self.socio1, "Plan API 3")

        self.cliente.force_authenticate(user=self.socio2.usuario)
        respuesta = self.cliente.get(f"/api/pagos/{pago_de_otro.id}/")
        self.assertIn(respuesta.status_code, (403, 404))

    def test_un_socio_no_ve_la_membresia_de_otro_socio(self):
        self._pagar(self.socio1, "Plan API 4")
        self.cliente.force_authenticate(user=self.socio2.usuario)
        respuesta = self.cliente.get("/api/membresias/")
        ids_devueltos = [fila["socio"] for fila in respuesta.data["results"]]
        self.assertNotIn(self.socio1.id, ids_devueltos)

    def test_un_socio_no_puede_registrar_pagos(self):
        plan = _crear_plan(nombre="Plan API 5")
        self.cliente.force_authenticate(user=self.socio1.usuario)
        respuesta = self.cliente.post(
            "/api/pagos/", {"socio": self.socio1.id, "plan": plan.id, "monto": plan.precio, "metodo": "EFECTIVO"}
        )
        self.assertEqual(respuesta.status_code, 403)
