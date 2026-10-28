# ============================================================
# core/management/commands/seed_data.py — DATOS DE PRUEBA
# Responsabilidad: dejar la base de datos lista para evaluar el
# sistema con un solo comando: python manage.py seed_data
#
# Qué crea: 1 administrador, 1 recepción, 2 instructores, 3 planes,
# 8 socios con membresías en los tres estados (activas, vencidas,
# congeladas) con sus pagos, clases de hoy y de la semana (una llena
# con lista de espera) y accesos del día (socios dentro y denegados).
#
# Es idempotente: si ya existen los socios, clases o accesos de
# demostración, no los vuelve a crear (evita violar la regla de "una
# sola membresía activa/congelada por socio" en una segunda corrida).
# Las membresías/pagos usan las funciones reales de servicios.py, no
# escriben estados a mano, salvo la fecha de las que se simulan
# vencidas (se retrocede la fecha y se deja que verificar_vencimiento
# haga la transición real).
# ============================================================
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accesos.models import Instalacion, RegistroAcceso, ResultadoAcceso, TipoAcceso
from accesos.servicios import validar_acceso
from clases.models import Clase, TipoClase
from clases.servicios import reservar_clase
from membresias.models import EstadoMembresia, MetodoPago, Plan
from membresias.servicios import congelar, registrar_pago, verificar_vencimiento
from socios.models import Socio
from socios.validadores import calcular_dv
from usuarios.models import Rol, Usuario

CONTRASENA_ADMIN = "Admin.2026"
CONTRASENA_RECEPCION = "Recepcion.2026"
CONTRASENA_INSTRUCTOR = "Instructor.2026"
CONTRASENA_SOCIO = "Socio.2026"

# (nombre, descripción, precio, duración en días, clases por semana)
PLANES = [
    ("Plan Básico", "Acceso a sala de musculación y cardio.", 19990, 30, 2),
    ("Plan Full", "Acceso ilimitado a sala y clases grupales.", 29990, 30, None),
    ("Plan Trimestral", "Plan Full con tarifa preferencial por 3 meses.", 74990, 90, 3),
]

# (username, nombre, apellido)
INSTRUCTORES = [
    ("instructor1", "Pedro", "Araya"),
    ("instructor2", "Daniela", "Muñoz"),
]

# (username, nombre, apellido, estado objetivo de la membresía)
SOCIOS = [
    ("socio1", "Ana", "Pérez", "ACTIVA"),
    ("socio2", "Bruno", "Silva", "ACTIVA"),
    ("socio3", "Carla", "Fuentes", "ACTIVA"),
    ("socio4", "Diego", "Rojas", "ACTIVA"),
    ("socio5", "Elena", "Castro", "VENCIDA"),
    ("socio6", "Felipe", "Morales", "VENCIDA"),
    ("socio7", "Gabriela", "Soto", "CONGELADA"),
    ("socio8", "Hugo", "Vargas", "CONGELADA"),
]

TIPOS_CLASE = ["Spinning", "Yoga", "Funcional", "Pilates"]


def _rut_demo(numero_base: int) -> str:
    """RUT de prueba determinista a partir de un número base (siempre el mismo por socio)."""
    cuerpo = str(numero_base)
    return f"{cuerpo}-{calcular_dv(cuerpo)}"


class Command(BaseCommand):
    help = "Carga datos de prueba de FitLife: usuarios, planes, socios, clases y accesos."

    @transaction.atomic
    def handle(self, *args, **options):
        self._titulo("DATOS DE PRUEBA DE FITLIFE")

        instalacion = Instalacion.obtener()
        self.stdout.write(f"  Instalación: {instalacion.nombre} (aforo máximo {instalacion.aforo_maximo})")

        admin = self._crear_administrador()
        recepcion = self._crear_recepcion()
        instructores = self._crear_instructores()
        planes = self._crear_planes()
        socios = self._crear_socios(planes, recepcion, admin)
        self._crear_clases(instructores, socios)
        self._crear_accesos_del_dia(socios, recepcion)

        self._resumen(admin, recepcion, instructores, socios)

    # ============================================================
    # USUARIOS
    # ============================================================
    def _crear_administrador(self) -> Usuario:
        self._titulo("Usuarios")
        admin, creado = Usuario.objects.get_or_create(
            username="admin",
            defaults={"email": "admin@fitlife.cl", "first_name": "Genesis", "last_name": "Quezada", "rol": Rol.ADMINISTRADOR},
        )
        admin.rol = Rol.ADMINISTRADOR
        admin.is_active = True
        admin.is_superuser = True
        admin.set_password(CONTRASENA_ADMIN)
        admin.save()
        self.stdout.write(f"  Administrador {'creado' if creado else 'actualizado'}: admin / {CONTRASENA_ADMIN}")
        return admin

    def _crear_recepcion(self) -> Usuario:
        recepcion, creado = Usuario.objects.get_or_create(
            username="recepcion1",
            defaults={"email": "recepcion1@fitlife.cl", "first_name": "Rosa", "last_name": "Díaz", "rol": Rol.RECEPCION},
        )
        recepcion.rol = Rol.RECEPCION
        recepcion.is_active = True
        recepcion.set_password(CONTRASENA_RECEPCION)
        recepcion.save()
        self.stdout.write(f"  Recepción {'creada' if creado else 'actualizada'}: recepcion1 / {CONTRASENA_RECEPCION}")
        return recepcion

    def _crear_instructores(self) -> list[Usuario]:
        instructores = []
        for username, nombre, apellido in INSTRUCTORES:
            instructor, creado = Usuario.objects.get_or_create(
                username=username,
                defaults={"email": f"{username}@fitlife.cl", "first_name": nombre, "last_name": apellido, "rol": Rol.INSTRUCTOR},
            )
            instructor.rol = Rol.INSTRUCTOR
            instructor.is_active = True
            instructor.set_password(CONTRASENA_INSTRUCTOR)
            instructor.save()
            instructores.append(instructor)
            self.stdout.write(f"  Instructor {'creado' if creado else 'actualizado'}: {username} / {CONTRASENA_INSTRUCTOR}")
        return instructores

    # ============================================================
    # PLANES
    # ============================================================
    def _crear_planes(self) -> dict[str, Plan]:
        self._titulo("Planes")
        planes = {}
        for nombre, descripcion, precio, duracion_dias, clases_por_semana in PLANES:
            plan, _ = Plan.objects.update_or_create(
                nombre=nombre,
                defaults={
                    "descripcion": descripcion, "precio": precio, "duracion_dias": duracion_dias,
                    "clases_por_semana": clases_por_semana, "activo": True,
                },
            )
            planes[nombre] = plan
        self.stdout.write(f"  {len(planes)} plan(es) listos.")
        return planes

    # ============================================================
    # SOCIOS, MEMBRESÍAS Y PAGOS
    # ============================================================
    def _crear_socios(self, planes, recepcion, admin) -> list[Socio]:
        self._titulo("Socios, membresías y pagos")
        lista_planes = list(planes.values())
        socios = []

        for indice, (username, nombre, apellido, estado_objetivo) in enumerate(SOCIOS):
            usuario, creado_usuario = Usuario.objects.get_or_create(
                username=username,
                defaults={"email": f"{username}@fitlife.cl", "first_name": nombre, "last_name": apellido, "rol": Rol.SOCIO},
            )
            usuario.rol = Rol.SOCIO
            usuario.is_active = True
            usuario.set_password(CONTRASENA_SOCIO)
            usuario.save()

            socio, creado_socio = Socio.objects.get_or_create(
                usuario=usuario,
                defaults={
                    "rut": _rut_demo(10_000_000 + indice),
                    "telefono": "+56 9 0000 000" + str(indice % 10),
                    "contacto_emergencia_nombre": "Contacto de emergencia",
                    "contacto_emergencia_telefono": "+56 9 1111 000" + str(indice % 10),
                },
            )
            socios.append(socio)

            if socio.membresias.exists():
                self.stdout.write(f"  {username}: ya tiene membresía, no se repite el pago.")
                continue

            plan = lista_planes[indice % len(lista_planes)]
            pago = registrar_pago(socio=socio, plan=plan, monto=plan.precio, metodo=MetodoPago.EFECTIVO, registrado_por=recepcion)
            membresia = pago.membresia

            if estado_objetivo == "VENCIDA":
                hoy = timezone.localdate()
                membresia.fecha_inicio = hoy - timedelta(days=45)
                membresia.fecha_fin = hoy - timedelta(days=10)
                membresia.save(update_fields=["fecha_inicio", "fecha_fin"])
                verificar_vencimiento(membresia)
            elif estado_objetivo == "CONGELADA":
                congelar(membresia, dias=15, autor=admin, observacion="Congelada en la carga de datos de prueba.")

            self.stdout.write(f"  {username} ({socio.rut}): membresía {estado_objetivo.lower()} con «{plan.nombre}».")

        return socios

    # ============================================================
    # CLASES Y RESERVAS
    # ============================================================
    def _crear_clases(self, instructores, socios) -> None:
        self._titulo("Clases y reservas")

        if Clase.objects.exists():
            self.stdout.write("  Ya existen clases; no se generan nuevas.")
            return

        tipos = {}
        for nombre in TIPOS_CLASE:
            tipo, _ = TipoClase.objects.get_or_create(nombre=nombre, defaults={"descripcion": f"Clase grupal de {nombre.lower()}."})
            tipos[nombre] = tipo

        ahora = timezone.now()

        clase_llena = Clase.objects.create(
            tipo=tipos["Spinning"], instructor=instructores[0], sala="Sala 1",
            inicio=ahora + timedelta(hours=3), fin=ahora + timedelta(hours=4), cupo_maximo=2,
        )
        clase_hoy = Clase.objects.create(
            tipo=tipos["Yoga"], instructor=instructores[1], sala="Sala 2",
            inicio=ahora + timedelta(hours=6), fin=ahora + timedelta(hours=7), cupo_maximo=10,
        )
        Clase.objects.create(
            tipo=tipos["Funcional"], instructor=instructores[0], sala="Sala 1",
            inicio=ahora + timedelta(days=2, hours=1), fin=ahora + timedelta(days=2, hours=2), cupo_maximo=8,
        )
        Clase.objects.create(
            tipo=tipos["Pilates"], instructor=instructores[1], sala="Sala 3",
            inicio=ahora + timedelta(days=4, hours=1), fin=ahora + timedelta(days=4, hours=2), cupo_maximo=6,
        )

        # Socios ACTIVA (los primeros cuatro de la lista) llenan la clase y hacen fila.
        activos = [s for s in socios if s.membresias.filter(estado=EstadoMembresia.ACTIVA).exists()][:4]
        for socio in activos[:2]:
            reservar_clase(socio, clase_llena)  # CONFIRMADA (cupo_maximo=2)
        for socio in activos[2:4]:
            reservar_clase(socio, clase_llena)  # EN_ESPERA

        if activos:
            reservar_clase(activos[0], clase_hoy)

        self.stdout.write(
            f"  4 clases creadas. «{clase_llena.tipo}» de hoy queda llena "
            f"({clase_llena.cupos_confirmados}/{clase_llena.cupo_maximo}) con "
            f"{clase_llena.en_lista_de_espera} socio(s) en lista de espera."
        )

    # ============================================================
    # ACCESOS DEL DÍA
    # ============================================================
    def _crear_accesos_del_dia(self, socios, recepcion) -> None:
        self._titulo("Accesos del día")

        if RegistroAcceso.objects.exists():
            self.stdout.write("  Ya existen registros de acceso; no se generan nuevos.")
            return

        por_username = {s.usuario.username: s for s in socios}

        # socio1 (ACTIVA) entra y se queda dentro.
        validar_acceso(token=str(por_username["socio1"].token_qr), tipo=TipoAcceso.ENTRADA, registrado_por=recepcion)

        # socio2 (ACTIVA) entra y sale: ya no queda dentro.
        validar_acceso(token=str(por_username["socio2"].token_qr), tipo=TipoAcceso.ENTRADA, registrado_por=recepcion)
        validar_acceso(token=str(por_username["socio2"].token_qr), tipo=TipoAcceso.SALIDA, registrado_por=recepcion)

        # socio5 (VENCIDA) y socio7 (CONGELADA): acceso denegado.
        validar_acceso(token=str(por_username["socio5"].token_qr), tipo=TipoAcceso.ENTRADA, registrado_por=recepcion)
        validar_acceso(token=str(por_username["socio7"].token_qr), tipo=TipoAcceso.ENTRADA, registrado_por=recepcion)

        # Token que no corresponde a ningún socio.
        validar_acceso(token="00000000-0000-0000-0000-000000000000", tipo=TipoAcceso.ENTRADA, registrado_por=recepcion)

        permitidos = RegistroAcceso.objects.filter(resultado=ResultadoAcceso.PERMITIDO).count()
        denegados = RegistroAcceso.objects.filter(resultado=ResultadoAcceso.DENEGADO).count()
        self.stdout.write(f"  Accesos del día: {permitidos} permitido(s), {denegados} denegado(s).")

    # ============================================================
    # RESUMEN Y CREDENCIALES
    # ============================================================
    def _titulo(self, texto):
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING(f"== {texto} =="))

    def _resumen(self, admin, recepcion, instructores, socios):
        self._titulo("Resumen")

        socio_activo = next(s for s in socios if s.usuario.username == "socio1")
        socio_vencido = next(s for s in socios if s.usuario.username == "socio5")

        self.stdout.write(self.style.SUCCESS("  Datos de prueba cargados correctamente."))
        self.stdout.write("")
        self.stdout.write("  Credenciales de demostración:")
        self.stdout.write(f"    admin       / {CONTRASENA_ADMIN}       (Administrador — también entra a /admin/)")
        self.stdout.write(f"    recepcion1  / {CONTRASENA_RECEPCION}  (Recepción)")
        self.stdout.write(f"    instructor1 / {CONTRASENA_INSTRUCTOR} (Instructor)")
        self.stdout.write(f"    instructor2 / {CONTRASENA_INSTRUCTOR} (Instructor)")
        self.stdout.write(f"    socio1..socio8 / {CONTRASENA_SOCIO} (Socio; socio1-4 ACTIVA, socio5-6 VENCIDA, socio7-8 CONGELADA)")
        self.stdout.write("")
        self.stdout.write("  Tokens QR de demostración:")
        self.stdout.write(f"    socio1 (membresía ACTIVA)  → {socio_activo.token_qr}")
        self.stdout.write(f"    socio5 (membresía VENCIDA) → {socio_vencido.token_qr}")
        self.stdout.write("")
        self.stdout.write("  Siguiente paso: python manage.py runserver")
