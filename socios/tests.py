# ============================================================
# socios/tests.py — VALIDACIÓN DE RUT, UNICIDAD Y TOKEN QR
# ============================================================
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework.test import APIClient

from usuarios.models import Rol, Usuario

from .models import Socio
from .validadores import calcular_dv, formatear_rut, limpiar_rut, validar_rut


def _crear_usuario_socio(username, email):
    return Usuario.objects.create_user(username=username, password="Clave.2026", rol=Rol.SOCIO, email=email)


class ValidadorRutTests(TestCase):
    """11.111.111-1 es el RUT de prueba que usa habitualmente la documentación chilena."""

    def test_rut_valido_no_lanza_error(self):
        validar_rut("11.111.111-1")  # no debe lanzar
        validar_rut("12345678-5")

    def test_rut_con_dv_incorrecto_lanza_error(self):
        with self.assertRaises(ValidationError):
            validar_rut("12345678-4")

    def test_rut_con_letras_en_el_cuerpo_lanza_error(self):
        with self.assertRaises(ValidationError):
            validar_rut("ABCDEFGH-5")

    def test_rut_demasiado_corto_lanza_error(self):
        with self.assertRaises(ValidationError):
            validar_rut("1-1")

    def test_calcular_dv_coincide_con_rut_de_prueba_conocido(self):
        self.assertEqual(calcular_dv("11111111"), "1")

    def test_formatear_rut_quita_puntos_y_normaliza(self):
        self.assertEqual(formatear_rut("12.345.678-5"), "12345678-5")
        self.assertEqual(limpiar_rut("12.345.678-5"), "123456785")


class SocioModeloTests(TestCase):
    def test_rut_se_guarda_normalizado_sin_puntos(self):
        usuario = _crear_usuario_socio("socio_rut1", "socio_rut1@fitlife.cl")
        socio = Socio.objects.create(usuario=usuario, rut="12.345.678-5")
        self.assertEqual(socio.rut, "12345678-5")

    def test_rut_duplicado_es_rechazado_por_la_base_de_datos(self):
        usuario1 = _crear_usuario_socio("socio_rut2", "socio_rut2@fitlife.cl")
        usuario2 = _crear_usuario_socio("socio_rut3", "socio_rut3@fitlife.cl")
        Socio.objects.create(usuario=usuario1, rut="12345678-5")

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Socio.objects.create(usuario=usuario2, rut="12.345.678-5")

    def test_regenerar_token_qr_invalida_el_token_anterior_de_inmediato(self):
        usuario = _crear_usuario_socio("socio_qr1", "socio_qr1@fitlife.cl")
        socio = Socio.objects.create(usuario=usuario, rut="9876543-3")
        token_anterior = socio.token_qr

        socio.regenerar_token_qr()

        self.assertNotEqual(socio.token_qr, token_anterior)
        self.assertFalse(Socio.objects.filter(token_qr=token_anterior).exists())
        self.assertTrue(Socio.objects.filter(token_qr=socio.token_qr).exists())


class ControlDeAccesoDeObjetoApiTests(TestCase):
    """Un socio jamás debe ver el perfil de otro socio, ni por la API ni filtrando su lista."""

    def setUp(self):
        self.cliente = APIClient()
        self.socio1 = Socio.objects.create(
            usuario=_crear_usuario_socio("socio_api1", "socio_api1@fitlife.cl"), rut="12345678-5"
        )
        self.socio2 = Socio.objects.create(
            usuario=_crear_usuario_socio("socio_api2", "socio_api2@fitlife.cl"), rut="9876543-3"
        )

    def test_un_socio_no_puede_ver_el_perfil_de_otro_socio(self):
        self.cliente.force_authenticate(user=self.socio2.usuario)
        respuesta = self.cliente.get(f"/api/socios/{self.socio1.id}/")
        self.assertIn(respuesta.status_code, (403, 404))

    def test_un_socio_si_puede_ver_su_propio_perfil(self):
        self.cliente.force_authenticate(user=self.socio1.usuario)
        respuesta = self.cliente.get(f"/api/socios/{self.socio1.id}/")
        self.assertEqual(respuesta.status_code, 200)

    def test_la_lista_de_socios_de_un_socio_solo_se_contiene_a_si_mismo(self):
        self.cliente.force_authenticate(user=self.socio2.usuario)
        respuesta = self.cliente.get("/api/socios/")
        ids_devueltos = [fila["id"] for fila in respuesta.data["results"]]
        self.assertEqual(ids_devueltos, [self.socio2.id])

    def test_sin_autenticar_la_api_exige_login(self):
        respuesta = self.cliente.get("/api/socios/")
        self.assertEqual(respuesta.status_code, 401)
