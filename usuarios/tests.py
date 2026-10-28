# ============================================================
# usuarios/tests.py — PRUEBAS DEL MODELO DE USUARIO Y LA AUTENTICACIÓN
# ============================================================
from django.test import TestCase
from django.urls import reverse

from .models import Rol, Usuario


class SincronizacionDeRolYStaffTests(TestCase):
    """is_staff debe quedar sincronizado SOLO con rol=ADMINISTRADOR."""

    def test_administrador_queda_como_staff(self):
        usuario = Usuario.objects.create_user(
            username="admin1", password="Clave.2026", rol=Rol.ADMINISTRADOR, email="admin1@fitlife.cl"
        )
        self.assertTrue(usuario.is_staff)
        self.assertTrue(usuario.es_administrador)

    def test_socio_no_queda_como_staff(self):
        usuario = Usuario.objects.create_user(
            username="socio1", password="Clave.2026", rol=Rol.SOCIO, email="socio1@fitlife.cl"
        )
        self.assertFalse(usuario.is_staff)
        self.assertTrue(usuario.es_socio)

    def test_recepcion_no_queda_como_staff(self):
        usuario = Usuario.objects.create_user(
            username="recep1", password="Clave.2026", rol=Rol.RECEPCION, email="recep1@fitlife.cl"
        )
        self.assertFalse(usuario.is_staff)

    def test_degradar_el_rol_quita_is_staff_al_guardar(self):
        """Si un administrador es degradado, pierde is_staff en el mismo guardado."""
        usuario = Usuario.objects.create_user(
            username="admin2", password="Clave.2026", rol=Rol.ADMINISTRADOR, email="admin2@fitlife.cl"
        )
        self.assertTrue(usuario.is_staff)

        usuario.rol = Rol.INSTRUCTOR
        usuario.save()
        usuario.refresh_from_db()
        self.assertFalse(usuario.is_staff)

    def test_rol_por_defecto_es_socio(self):
        usuario = Usuario.objects.create_user(username="sinrol", password="Clave.2026", email="sinrol@fitlife.cl")
        self.assertEqual(usuario.rol, Rol.SOCIO)


class AutenticacionWebTests(TestCase):
    """Login/logout por sesión y la regla de 'todo exige login salvo inicio y login'."""

    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            username="socio_test", password="Clave.2026", rol=Rol.SOCIO, email="socio_test@fitlife.cl"
        )

    def test_portada_publica_no_exige_login(self):
        respuesta = self.client.get(reverse("core:inicio"))
        self.assertEqual(respuesta.status_code, 200)

    def test_panel_exige_login(self):
        respuesta = self.client.get(reverse("core:panel"))
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn(reverse("usuarios:login"), respuesta.url)

    def test_login_correcto_permite_entrar_al_panel(self):
        respuesta = self.client.post(
            reverse("usuarios:login"), {"username": "socio_test", "password": "Clave.2026"}
        )
        self.assertEqual(respuesta.status_code, 302)

        respuesta_panel = self.client.get(reverse("core:panel"))
        self.assertEqual(respuesta_panel.status_code, 200)

    def test_login_con_clave_incorrecta_no_autentica(self):
        respuesta = self.client.post(
            reverse("usuarios:login"), {"username": "socio_test", "password": "clave-mala"}
        )
        self.assertEqual(respuesta.status_code, 200)  # vuelve a mostrar el formulario con error
        self.assertFalse(respuesta.wsgi_request.user.is_authenticated)

    def test_logout_por_get_no_esta_permitido(self):
        self.client.login(username="socio_test", password="Clave.2026")
        respuesta = self.client.get(reverse("usuarios:logout"))
        self.assertEqual(respuesta.status_code, 405)

    def test_logout_por_post_cierra_la_sesion(self):
        self.client.login(username="socio_test", password="Clave.2026")
        respuesta = self.client.post(reverse("usuarios:logout"))
        self.assertEqual(respuesta.status_code, 302)

        respuesta_panel = self.client.get(reverse("core:panel"))
        self.assertEqual(respuesta_panel.status_code, 302)  # ya no hay sesión
