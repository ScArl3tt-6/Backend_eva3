# ============================================================
# clases/tests.py — CUPOS, LISTA DE ESPERA, CANCELACIÓN Y ASISTENCIA
# ============================================================
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from membresias.models import EstadoMembresia, Membresia, Plan
from socios.models import Socio
from socios.validadores import calcular_dv
from usuarios.models import Rol, Usuario

from .models import Clase, EstadoClase, EstadoReserva, Reserva, TipoClase
from .servicios import (
    CancelacionFueraDePlazoError,
    ClaseNoDisponibleError,
    LimiteSemanalError,
    MembresiaNoActivaError,
    ReservaDuplicadaError,
    TransicionInvalidaError,
    cancelar_clase,
    cancelar_reserva,
    marcar_asistencia,
    reservar_clase,
)


def _crear_socio(username, clases_por_semana=None, dias_vigencia=30):
    usuario = Usuario.objects.create_user(
        username=username, password="Clave.2026", rol=Rol.SOCIO, email=f"{username}@fitlife.cl"
    )
    sufijo = str(abs(hash(username)) % 9000000 + 1000000)
    socio = Socio.objects.create(usuario=usuario, rut=f"{sufijo}-{calcular_dv(sufijo)}")
    plan = Plan.objects.create(
        nombre=f"Plan {username}", precio=10000, duracion_dias=60, clases_por_semana=clases_por_semana
    )
    Membresia.objects.create(
        socio=socio, plan=plan, fecha_inicio=timezone.localdate(),
        fecha_fin=timezone.localdate() + timedelta(days=dias_vigencia), estado=EstadoMembresia.ACTIVA,
    )
    return socio


def _crear_instructor(username="instructor1"):
    """get_or_create: varias clases de una misma prueba pueden compartir instructor por defecto."""
    usuario, _ = Usuario.objects.get_or_create(
        username=username, defaults={"email": f"{username}@fitlife.cl", "rol": Rol.INSTRUCTOR}
    )
    usuario.set_password("Clave.2026")
    usuario.save()
    return usuario


def _crear_clase(instructor=None, inicio=None, cupo_maximo=1, estado=EstadoClase.PROGRAMADA):
    instructor = instructor or _crear_instructor()
    tipo = TipoClase.objects.create(nombre=f"Tipo-{Clase.objects.count()}-{timezone.now().timestamp()}")
    inicio = inicio or (timezone.now() + timedelta(days=1))
    return Clase.objects.create(
        tipo=tipo, instructor=instructor, sala="Sala 1", inicio=inicio, fin=inicio + timedelta(hours=1),
        cupo_maximo=cupo_maximo, estado=estado,
    )


class ReservarClaseTests(TestCase):
    def test_reserva_confirmada_cuando_hay_cupo(self):
        socio = _crear_socio("socio_res1")
        clase = _crear_clase(cupo_maximo=2)
        reserva = reservar_clase(socio, clase)
        self.assertEqual(reserva.estado, EstadoReserva.CONFIRMADA)

    def test_reserva_en_espera_cuando_no_hay_cupo(self):
        clase = _crear_clase(cupo_maximo=1)
        socio1 = _crear_socio("socio_res2a")
        socio2 = _crear_socio("socio_res2b")

        reservar_clase(socio1, clase)
        reserva2 = reservar_clase(socio2, clase)

        self.assertEqual(reserva2.estado, EstadoReserva.EN_ESPERA)
        self.assertEqual(reserva2.posicion_espera, 1)

    def test_no_se_puede_reservar_sin_membresia_activa(self):
        usuario = Usuario.objects.create_user(username="socio_sin_mem", password="Clave.2026", rol=Rol.SOCIO, email="s@fitlife.cl")
        socio = Socio.objects.create(usuario=usuario, rut="12345678-5")
        clase = _crear_clase()
        with self.assertRaises(MembresiaNoActivaError):
            reservar_clase(socio, clase)

    def test_no_se_puede_reservar_si_la_membresia_vence_antes_de_la_clase(self):
        socio = _crear_socio("socio_res3", dias_vigencia=2)
        clase = _crear_clase(inicio=timezone.now() + timedelta(days=10))
        with self.assertRaises(MembresiaNoActivaError):
            reservar_clase(socio, clase)

    def test_se_puede_reservar_si_la_membresia_cubre_la_fecha_de_la_clase(self):
        socio = _crear_socio("socio_res4", dias_vigencia=15)
        clase = _crear_clase(inicio=timezone.now() + timedelta(days=10))
        reserva = reservar_clase(socio, clase)
        self.assertEqual(reserva.estado, EstadoReserva.CONFIRMADA)

    def test_no_se_puede_reservar_una_clase_cancelada(self):
        socio = _crear_socio("socio_res5")
        clase = _crear_clase(estado=EstadoClase.CANCELADA)
        with self.assertRaises(ClaseNoDisponibleError):
            reservar_clase(socio, clase)

    def test_no_se_puede_reservar_una_clase_finalizada(self):
        socio = _crear_socio("socio_res6")
        clase = _crear_clase(estado=EstadoClase.FINALIZADA)
        with self.assertRaises(ClaseNoDisponibleError):
            reservar_clase(socio, clase)

    def test_no_se_puede_reservar_una_clase_que_ya_paso(self):
        socio = _crear_socio("socio_res7")
        clase = _crear_clase(inicio=timezone.now() - timedelta(hours=2))
        with self.assertRaises(ClaseNoDisponibleError):
            reservar_clase(socio, clase)

    def test_no_se_puede_reservar_dos_veces_la_misma_clase(self):
        socio = _crear_socio("socio_res8")
        clase = _crear_clase(cupo_maximo=5)
        reservar_clase(socio, clase)
        with self.assertRaises(ReservaDuplicadaError):
            reservar_clase(socio, clase)

    def test_limite_semanal_del_plan_es_respetado(self):
        socio = _crear_socio("socio_res9", clases_por_semana=1)
        # Lunes de la PRÓXIMA semana a partir de hoy: así "lunes + 1/2 días" cae
        # siempre en el futuro sin importar qué día de la semana se corra la prueba.
        proxima_semana = timezone.now() + timedelta(days=7)
        lunes = (proxima_semana - timedelta(days=proxima_semana.weekday())).replace(
            hour=10, minute=0, second=0, microsecond=0
        )
        clase1 = _crear_clase(inicio=lunes + timedelta(days=1))
        clase2 = _crear_clase(inicio=lunes + timedelta(days=2))

        reservar_clase(socio, clase1)
        with self.assertRaises(LimiteSemanalError):
            reservar_clase(socio, clase2)


class CancelarReservaTests(TestCase):
    def test_cancelar_confirmada_promueve_al_primero_en_espera(self):
        clase = _crear_clase(cupo_maximo=1, inicio=timezone.now() + timedelta(days=2))
        socio1 = _crear_socio("socio_canc1")
        socio2 = _crear_socio("socio_canc2")

        r1 = reservar_clase(socio1, clase)
        r2 = reservar_clase(socio2, clase)
        self.assertEqual(r2.estado, EstadoReserva.EN_ESPERA)

        cancelar_reserva(r1)

        r2.refresh_from_db()
        self.assertEqual(r2.estado, EstadoReserva.CONFIRMADA)
        self.assertIsNone(r2.posicion_espera)

    def test_cancelar_en_espera_reordena_las_posiciones_siguientes(self):
        clase = _crear_clase(cupo_maximo=1, inicio=timezone.now() + timedelta(days=2))
        socio1 = _crear_socio("socio_canc3")
        socio2 = _crear_socio("socio_canc4")
        socio3 = _crear_socio("socio_canc5")

        reservar_clase(socio1, clase)  # CONFIRMADA
        r2 = reservar_clase(socio2, clase)  # EN_ESPERA posición 1
        r3 = reservar_clase(socio3, clase)  # EN_ESPERA posición 2

        cancelar_reserva(r2)

        r3.refresh_from_db()
        self.assertEqual(r3.estado, EstadoReserva.EN_ESPERA)
        self.assertEqual(r3.posicion_espera, 1)

    def test_cancelacion_fuera_de_plazo_es_rechazada(self):
        clase = _crear_clase(cupo_maximo=1, inicio=timezone.now() + timedelta(minutes=5))
        socio = _crear_socio("socio_canc6")
        reserva = reservar_clase(socio, clase)
        with self.assertRaises(CancelacionFueraDePlazoError):
            cancelar_reserva(reserva)

    def test_nunca_hay_sobrecupo_bajo_reservas_sucesivas(self):
        clase = _crear_clase(cupo_maximo=1, inicio=timezone.now() + timedelta(days=2))
        socios = [_crear_socio(f"socio_sobrecupo{i}") for i in range(3)]
        for socio in socios:
            reservar_clase(socio, clase)

        confirmadas = Reserva.objects.filter(clase=clase, estado=EstadoReserva.CONFIRMADA).count()
        self.assertLessEqual(confirmadas, clase.cupo_maximo)
        self.assertEqual(confirmadas, 1)


class CancelarClaseTests(TestCase):
    def test_cancelar_la_clase_cancela_sus_reservas_activas(self):
        clase = _crear_clase(cupo_maximo=1, inicio=timezone.now() + timedelta(days=2))
        socio1 = _crear_socio("socio_cc1")
        socio2 = _crear_socio("socio_cc2")

        r1 = reservar_clase(socio1, clase)  # CONFIRMADA
        r2 = reservar_clase(socio2, clase)  # EN_ESPERA

        cancelar_clase(clase)

        clase.refresh_from_db()
        r1.refresh_from_db()
        r2.refresh_from_db()
        self.assertEqual(clase.estado, EstadoClase.CANCELADA)
        self.assertEqual(r1.estado, EstadoReserva.CANCELADA)
        self.assertEqual(r2.estado, EstadoReserva.CANCELADA)


class MarcarAsistenciaTests(TestCase):
    def test_no_se_puede_marcar_asistencia_antes_de_iniciar_la_clase(self):
        clase = _crear_clase(cupo_maximo=1, inicio=timezone.now() + timedelta(hours=2))
        socio = _crear_socio("socio_asis1")
        reserva = reservar_clase(socio, clase)
        with self.assertRaises(TransicionInvalidaError):
            marcar_asistencia(reserva, asistio=True)

    def test_marcar_asistencia_despues_de_iniciada_la_clase(self):
        clase = _crear_clase(cupo_maximo=1, inicio=timezone.now() - timedelta(minutes=10))
        clase.fin = clase.inicio + timedelta(hours=1)
        clase.save(update_fields=["fin"])
        socio = _crear_socio("socio_asis2")
        # La reserva se crea directo (reservar_clase rechazaría una clase ya iniciada).
        reserva = Reserva.objects.create(clase=clase, socio=socio, estado=EstadoReserva.CONFIRMADA)

        marcar_asistencia(reserva, asistio=True)
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado, EstadoReserva.ASISTIO)


class RestriccionesDeBaseDeDatosTests(TestCase):
    def test_no_puede_haber_dos_reservas_activas_del_mismo_socio_en_la_misma_clase(self):
        clase = _crear_clase(cupo_maximo=5)
        socio = _crear_socio("socio_rbd1")
        Reserva.objects.create(clase=clase, socio=socio, estado=EstadoReserva.CONFIRMADA)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Reserva.objects.create(clase=clase, socio=socio, estado=EstadoReserva.EN_ESPERA, posicion_espera=1)

    def test_clase_con_cupo_cero_es_rechazada_por_la_base_de_datos(self):
        instructor = _crear_instructor("instructor_rbd")
        tipo = TipoClase.objects.create(nombre="Tipo RBD")
        inicio = timezone.now() + timedelta(days=1)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Clase.objects.create(
                    tipo=tipo, instructor=instructor, sala="Sala X", inicio=inicio,
                    fin=inicio + timedelta(hours=1), cupo_maximo=0,
                )


class ControlDeAccesoDeObjetoApiTests(TestCase):
    """Un socio jamás debe ver ni cancelar la reserva de otro socio vía API."""

    def setUp(self):
        self.cliente = APIClient()
        self.clase = _crear_clase(cupo_maximo=5, inicio=timezone.now() + timedelta(days=2))
        self.socio1 = _crear_socio("socio_res_api1")
        self.socio2 = _crear_socio("socio_res_api2")
        self.reserva1 = reservar_clase(self.socio1, self.clase)
        self.reserva2 = reservar_clase(self.socio2, self.clase)

    def test_un_socio_no_ve_la_reserva_de_otro_socio_en_la_lista(self):
        self.cliente.force_authenticate(user=self.socio2.usuario)
        respuesta = self.cliente.get("/api/reservas/")
        ids_devueltos = [fila["id"] for fila in respuesta.data["results"]]
        self.assertEqual(ids_devueltos, [self.reserva2.id])

    def test_un_socio_no_puede_cancelar_la_reserva_de_otro_socio(self):
        self.cliente.force_authenticate(user=self.socio2.usuario)
        respuesta = self.cliente.post(f"/api/reservas/{self.reserva1.id}/cancelar/")
        self.assertIn(respuesta.status_code, (403, 404))

        self.reserva1.refresh_from_db()
        self.assertEqual(self.reserva1.estado, EstadoReserva.CONFIRMADA)

    def test_un_socio_si_puede_cancelar_su_propia_reserva(self):
        clase_lejana = _crear_clase(cupo_maximo=5, inicio=timezone.now() + timedelta(days=5))
        reserva = reservar_clase(self.socio1, clase_lejana)

        self.cliente.force_authenticate(user=self.socio1.usuario)
        respuesta = self.cliente.post(f"/api/reservas/{reserva.id}/cancelar/")
        self.assertEqual(respuesta.status_code, 200)
