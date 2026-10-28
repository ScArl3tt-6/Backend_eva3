# ============================================================
# accesos/tests.py — VALIDACIÓN DE ACCESO, AFORO Y ANTIPASSBACK
# ============================================================
import threading
from datetime import timedelta

from django.db import connection
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient

from membresias.models import EstadoMembresia, Membresia, Plan
from membresias.servicios import congelar
from socios.models import Socio
from socios.validadores import calcular_dv
from usuarios.models import Rol, Usuario

from .models import Instalacion, ResultadoAcceso, TipoAcceso
from .servicios import ocupacion_actual, validar_acceso


def _crear_socio(username):
    usuario = Usuario.objects.create_user(
        username=username, password="Clave.2026", rol=Rol.SOCIO, email=f"{username}@fitlife.cl"
    )
    sufijo = str(abs(hash(username)) % 9000000 + 1000000)
    rut = f"{sufijo}-{calcular_dv(sufijo)}"
    return Socio.objects.create(usuario=usuario, rut=rut)


def _crear_socio_con_membresia_activa(username):
    socio = _crear_socio(username)
    plan = Plan.objects.create(nombre=f"Plan {username}", precio=10000, duracion_dias=30)
    Membresia.objects.create(
        socio=socio, plan=plan, fecha_inicio=timezone.localdate(),
        fecha_fin=timezone.localdate() + timedelta(days=30), estado=EstadoMembresia.ACTIVA,
    )
    return socio


def _fijar_aforo(maximo: int) -> Instalacion:
    instalacion = Instalacion.obtener()
    instalacion.aforo_maximo = maximo
    instalacion.save(update_fields=["aforo_maximo"])
    return instalacion


class ValidarAccesoTests(TestCase):
    def setUp(self):
        _fijar_aforo(10)

    def test_token_inexistente_es_denegado_y_queda_registrado(self):
        registro = validar_acceso(token="00000000-0000-0000-0000-000000000000", tipo=TipoAcceso.ENTRADA)
        self.assertEqual(registro.resultado, ResultadoAcceso.DENEGADO)
        self.assertIsNone(registro.socio)
        self.assertIn("no corresponde", registro.motivo)

    def test_token_con_texto_basura_no_rompe_y_queda_denegado(self):
        registro = validar_acceso(token="esto-no-es-un-uuid", tipo=TipoAcceso.ENTRADA)
        self.assertEqual(registro.resultado, ResultadoAcceso.DENEGADO)
        self.assertIsNone(registro.socio)

    def test_membresia_vencida_deniega_el_acceso(self):
        socio = _crear_socio("socio_acc_venc")
        plan = Plan.objects.create(nombre="Plan vencido", precio=5000, duracion_dias=30)
        Membresia.objects.create(
            socio=socio, plan=plan, fecha_inicio=timezone.localdate() - timedelta(days=60),
            fecha_fin=timezone.localdate() - timedelta(days=1), estado=EstadoMembresia.ACTIVA,
        )
        registro = validar_acceso(token=str(socio.token_qr), tipo=TipoAcceso.ENTRADA)
        self.assertEqual(registro.resultado, ResultadoAcceso.DENEGADO)
        self.assertIn("vencida", registro.motivo)

    def test_membresia_congelada_deniega_el_acceso(self):
        socio = _crear_socio_con_membresia_activa("socio_acc_frz")
        congelar(socio.membresias.get(), dias=10)
        registro = validar_acceso(token=str(socio.token_qr), tipo=TipoAcceso.ENTRADA)
        self.assertEqual(registro.resultado, ResultadoAcceso.DENEGADO)
        self.assertIn("congelada", registro.motivo)

    def test_sin_membresia_registrada_deniega_el_acceso(self):
        socio = _crear_socio("socio_acc_sin")
        registro = validar_acceso(token=str(socio.token_qr), tipo=TipoAcceso.ENTRADA)
        self.assertEqual(registro.resultado, ResultadoAcceso.DENEGADO)
        self.assertIn("no tiene una membresía", registro.motivo)

    def test_entrada_valida_se_permite(self):
        socio = _crear_socio_con_membresia_activa("socio_acc_ok")
        registro = validar_acceso(token=str(socio.token_qr), tipo=TipoAcceso.ENTRADA)
        self.assertEqual(registro.resultado, ResultadoAcceso.PERMITIDO)

    def test_antipassback_rechaza_segunda_entrada_sin_salida(self):
        socio = _crear_socio_con_membresia_activa("socio_acc_antip")
        validar_acceso(token=str(socio.token_qr), tipo=TipoAcceso.ENTRADA)

        registro2 = validar_acceso(token=str(socio.token_qr), tipo=TipoAcceso.ENTRADA)
        self.assertEqual(registro2.resultado, ResultadoAcceso.DENEGADO)
        self.assertIn("antipassback", registro2.motivo)

    def test_salida_sin_entrada_abierta_es_denegada(self):
        socio = _crear_socio_con_membresia_activa("socio_acc_salsin")
        registro = validar_acceso(token=str(socio.token_qr), tipo=TipoAcceso.SALIDA)
        self.assertEqual(registro.resultado, ResultadoAcceso.DENEGADO)
        self.assertIn("entrada abierta", registro.motivo)

    def test_salida_despues_de_entrada_se_permite_y_libera_antipassback(self):
        socio = _crear_socio_con_membresia_activa("socio_acc_ciclo")
        validar_acceso(token=str(socio.token_qr), tipo=TipoAcceso.ENTRADA)
        salida = validar_acceso(token=str(socio.token_qr), tipo=TipoAcceso.SALIDA)
        self.assertEqual(salida.resultado, ResultadoAcceso.PERMITIDO)

        # Tras la salida, puede volver a entrar.
        segunda_entrada = validar_acceso(token=str(socio.token_qr), tipo=TipoAcceso.ENTRADA)
        self.assertEqual(segunda_entrada.resultado, ResultadoAcceso.PERMITIDO)

    def test_aforo_completo_deniega_la_entrada_y_queda_registrado(self):
        _fijar_aforo(1)
        socio1 = _crear_socio_con_membresia_activa("socio_aforo1")
        socio2 = _crear_socio_con_membresia_activa("socio_aforo2")

        primera = validar_acceso(token=str(socio1.token_qr), tipo=TipoAcceso.ENTRADA)
        segunda = validar_acceso(token=str(socio2.token_qr), tipo=TipoAcceso.ENTRADA)

        self.assertEqual(primera.resultado, ResultadoAcceso.PERMITIDO)
        self.assertEqual(segunda.resultado, ResultadoAcceso.DENEGADO)
        self.assertIn("Aforo completo", segunda.motivo)
        self.assertEqual(ocupacion_actual(), 1)


class RegeneracionDeTokenQrTests(TestCase):
    def setUp(self):
        _fijar_aforo(10)

    def test_token_anterior_queda_denegado_tras_regenerar(self):
        socio = _crear_socio_con_membresia_activa("socio_qr_regen")
        token_anterior = str(socio.token_qr)

        socio.regenerar_token_qr()

        registro = validar_acceso(token=token_anterior, tipo=TipoAcceso.ENTRADA)
        self.assertEqual(registro.resultado, ResultadoAcceso.DENEGADO)
        self.assertIsNone(registro.socio)

        registro_nuevo = validar_acceso(token=str(socio.token_qr), tipo=TipoAcceso.ENTRADA)
        self.assertEqual(registro_nuevo.resultado, ResultadoAcceso.PERMITIDO)


class ConcurrenciaAforoTests(TransactionTestCase):
    """Prueba real de condición de carrera: dos ENTRADAs a la vez, aforo=1."""

    def test_dos_entradas_simultaneas_con_aforo_uno_solo_permite_una(self):
        _fijar_aforo(1)
        socio1 = _crear_socio_con_membresia_activa("socio_conc1")
        socio2 = _crear_socio_con_membresia_activa("socio_conc2")

        resultados = []
        barrera = threading.Barrier(2)

        def intentar(socio):
            try:
                barrera.wait(timeout=5)
                registro = validar_acceso(token=str(socio.token_qr), tipo=TipoAcceso.ENTRADA)
                resultados.append(registro.resultado)
            finally:
                connection.close()

        hilo1 = threading.Thread(target=intentar, args=(socio1,))
        hilo2 = threading.Thread(target=intentar, args=(socio2,))
        hilo1.start()
        hilo2.start()
        hilo1.join()
        hilo2.join()

        self.assertEqual(sorted(resultados), [ResultadoAcceso.DENEGADO, ResultadoAcceso.PERMITIDO])
        self.assertEqual(ocupacion_actual(), 1)


class ControlDeAccesoDeObjetoApiTests(TestCase):
    """Un socio jamás debe ver los accesos de otro socio vía API."""

    def setUp(self):
        _fijar_aforo(10)
        self.cliente = APIClient()
        self.socio1 = _crear_socio_con_membresia_activa("socio_acc_api1")
        self.socio2 = _crear_socio_con_membresia_activa("socio_acc_api2")

    def test_un_socio_no_ve_los_accesos_de_otro_socio_en_la_lista(self):
        registro_propio = validar_acceso(token=str(self.socio2.token_qr), tipo=TipoAcceso.ENTRADA)
        validar_acceso(token=str(self.socio1.token_qr), tipo=TipoAcceso.ENTRADA)

        self.cliente.force_authenticate(user=self.socio2.usuario)
        respuesta = self.cliente.get("/api/accesos/")
        ids_devueltos = [fila["id"] for fila in respuesta.data["results"]]
        self.assertEqual(ids_devueltos, [registro_propio.id])

    def test_un_socio_no_puede_llamar_al_endpoint_de_validar_acceso(self):
        self.cliente.force_authenticate(user=self.socio1.usuario)
        respuesta = self.cliente.post(
            "/api/accesos/validar/", {"token": str(self.socio1.token_qr), "tipo": TipoAcceso.ENTRADA}
        )
        self.assertEqual(respuesta.status_code, 403)

    def test_recepcion_si_puede_llamar_al_endpoint_de_validar_acceso(self):
        recepcion = Usuario.objects.create_user(
            username="recepcion_api1", password="Clave.2026", rol=Rol.RECEPCION, email="recepcion_api1@fitlife.cl"
        )
        self.cliente.force_authenticate(user=recepcion)
        respuesta = self.cliente.post(
            "/api/accesos/validar/", {"token": str(self.socio1.token_qr), "tipo": TipoAcceso.ENTRADA}
        )
        self.assertEqual(respuesta.status_code, 201)
        self.assertEqual(respuesta.data["resultado"], ResultadoAcceso.PERMITIDO)
