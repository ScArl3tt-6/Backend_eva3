# ============================================================
# core/tests.py — PROTECCIÓN DE LA DOCUMENTACIÓN DE LA API
# El esquema OpenAPI y Swagger/ReDoc no son información pública:
# exigen sesión iniciada (o un JWT válido), igual que el resto de
# la API.
# ============================================================
from django.test import TestCase

from usuarios.models import Rol, Usuario


class DocumentacionProtegidaTests(TestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_user(
            username="admin_docs", password="Clave.2026", rol=Rol.ADMINISTRADOR, email="admin_docs@fitlife.cl"
        )

    def test_schema_exige_sesion_iniciada(self):
        respuesta = self.client.get("/api/schema/")
        self.assertEqual(respuesta.status_code, 401)

    def test_swagger_exige_sesion_iniciada(self):
        respuesta = self.client.get("/api/docs/")
        self.assertEqual(respuesta.status_code, 401)

    def test_redoc_exige_sesion_iniciada(self):
        respuesta = self.client.get("/api/redoc/")
        self.assertEqual(respuesta.status_code, 401)

    def test_con_sesion_iniciada_se_puede_ver_el_schema(self):
        self.client.force_login(self.admin)
        respuesta = self.client.get("/api/schema/")
        self.assertEqual(respuesta.status_code, 200)

    def test_con_sesion_iniciada_se_puede_ver_swagger(self):
        self.client.force_login(self.admin)
        respuesta = self.client.get("/api/docs/")
        self.assertEqual(respuesta.status_code, 200)
