# ============================================================
# settings.py — CONFIGURACIÓN CENTRAL DEL PROYECTO
# Proyecto: FitLife — Plataforma de control de asistencia y reserva
# de clases para un gimnasio.
# Alumna: Genesis Quezada Sanzana — EVA-3 Desarrollo Backend
#
# Responsabilidad: reunir en un solo lugar la configuración de
# Django, DRF, JWT, OpenAPI, PostgreSQL y localización chilena.
# Ningún secreto ni dato de la alumna está escrito a mano: todo se
# lee del archivo .env con python-decouple.
# ============================================================

import sys
from datetime import timedelta
from pathlib import Path

from decouple import Csv, config
from django.contrib.messages import constants as mensajes

# ============================================================
# BLOQUE 1 — RUTAS BASE
# ============================================================
BASE_DIR = Path(__file__).resolve().parent.parent


# ============================================================
# BLOQUE 2 — IDENTIFICACIÓN DE LA ALUMNA Y NOMBRE COMERCIAL
# Llegan a todas las plantillas vía core.context_processors.datos_alumno
# y se exigen en el footer de cada pantalla.
# ============================================================
ALUMNO_NOMBRE = config("ALUMNO_NOMBRE", default="Genesis Quezada Sanzana")
NOMBRE_COMERCIAL = config("NOMBRE_COMERCIAL", default="FitLife")


# ============================================================
# BLOQUE 3 — SEGURIDAD Y ENTORNO
# SECRET_KEY no tiene valor por omisión a propósito: si falta en el
# .env, el proyecto debe fallar al arrancar en vez de usar una clave
# insegura conocida.
# ============================================================
SECRET_KEY = config("SECRET_KEY")
DEBUG = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS",
    default="localhost,127.0.0.1,[::1],testserver",
    cast=Csv(),
)

# ============================================================
# BLOQUE 3-B — HTTPS DETRÁS DE UN PROXY (NGINX + LET'S ENCRYPT)
# En local DETRAS_DE_PROXY_HTTPS queda en False: el sitio funciona
# por HTTP, sin cookies "Secure" ni HSTS.
#
# En el servidor EC2, Nginx recibe la conexión HTTPS del navegador y
# la reenvía a Gunicorn por HTTP agregando X-Forwarded-Proto (gracias
# a "include proxy_params"). Sin esta variable, Django no tiene forma
# de saber que la conexión original era segura y las cookies
# "Secure"/CSRF fallarían detrás del proxy.
# ============================================================
CSRF_TRUSTED_ORIGINS = config("CSRF_TRUSTED_ORIGINS", default="", cast=Csv())
DETRAS_DE_PROXY_HTTPS = config("DETRAS_DE_PROXY_HTTPS", default=False, cast=bool)

if DETRAS_DE_PROXY_HTTPS:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 3600


# ============================================================
# BLOQUE 4 — APLICACIONES INSTALADAS
# Las apps de negocio se agregan una por una en cada fase del
# desarrollo (ver commits); "core" no tiene modelos propios y va
# primero porque su CoreConfig concentra la infraestructura
# transversal (context processors, manejador de excepciones).
# ============================================================
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

TERCEROS_APPS = [
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "django_filters",
    "drf_spectacular",
]

APPS_NEGOCIO = [
    "core.apps.CoreConfig",
    "usuarios.apps.UsuariosConfig",
    "socios.apps.SociosConfig",
    "membresias.apps.MembresiasConfig",
    "accesos.apps.AccesosConfig",
    "clases.apps.ClasesConfig",
]

INSTALLED_APPS = DJANGO_APPS + TERCEROS_APPS + APPS_NEGOCIO


# ============================================================
# BLOQUE 5 — MIDDLEWARE
# ============================================================
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "fitlife.urls"


# ============================================================
# BLOQUE 6 — PLANTILLAS
# ============================================================
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.datos_alumno",
            ],
        },
    },
]

WSGI_APPLICATION = "fitlife.wsgi.application"
ASGI_APPLICATION = "fitlife.asgi.application"


# ============================================================
# BLOQUE 7 — BASE DE DATOS POSTGRESQL
# Motor obligatorio django.db.backends.postgresql. Los parámetros de
# conexión se leen del .env; cambiar de servidor no exige tocar código.
# ============================================================
DATABASES = {
    "default": {
        "ENGINE": config("DB_ENGINE", default="django.db.backends.postgresql"),
        "NAME": config("DB_NAME", default="fitlife_db"),
        "USER": config("DB_USER", default="postgres"),
        "PASSWORD": config("DB_PASSWORD", default=""),
        "HOST": config("DB_HOST", default="localhost"),
        "PORT": config("DB_PORT", default="5432"),
        "ATOMIC_REQUESTS": False,
        "TEST": {"NAME": "test_" + config("DB_NAME", default="fitlife_db")},
    }
}


# ============================================================
# BLOQUE 7-B — REGLAS DE NEGOCIO CONFIGURABLES
# Los servicios.py de cada app leen estos valores desde settings
# (nunca llaman a decouple directamente), para que todo el .env se
# resuelva en un único lugar del proyecto.
#
# El aforo máximo del gimnasio NO está aquí: vive en la base de
# datos (accesos.Instalacion, editable desde el Django Admin) para
# poder bloquearlo con select_for_update() durante la validación de
# accesos y evitar condiciones de carrera.
# ============================================================
CONGELAMIENTO_DIAS_MIN = config("CONGELAMIENTO_DIAS_MIN", default=7, cast=int)
CONGELAMIENTO_DIAS_MAX = config("CONGELAMIENTO_DIAS_MAX", default=60, cast=int)
CANCELACION_MINUTOS_LIMITE = config("CANCELACION_MINUTOS_LIMITE", default=60, cast=int)


# ============================================================
# BLOQUE 8 — MODELO DE USUARIO PERSONALIZADO
# Usuario con campo "rol"; is_staff se sincroniza solo para
# ADMINISTRADOR (ver usuarios/models.py). Se define ahora, antes de
# aplicar ninguna migración real, para no migrar el usuario a mitad
# de camino.
# ============================================================
AUTH_USER_MODEL = "usuarios.Usuario"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ============================================================
# BLOQUE 8-B — SESIÓN Y LOGIN
# TODA la aplicación web exige sesión iniciada salvo la portada
# pública y el login (criterio de seguridad de la pauta).
# SESSION_COOKIE_AGE es configurable por .env.
# ============================================================
LOGIN_URL = "/cuentas/login/"
LOGIN_REDIRECT_URL = "/panel/"
LOGOUT_REDIRECT_URL = "/"
SESSION_COOKIE_AGE = config("SESSION_COOKIE_AGE", default=1209600, cast=int)


# ============================================================
# BLOQUE 9 — DJANGO REST FRAMEWORK
# Autenticación por JWT (API) o por sesión (para la Browsable API y
# el dashboard de aforo consumido desde las plantillas con fetch).
# Permiso restrictivo por defecto: cada endpoint público declara
# AllowAny explícitamente.
# ============================================================
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "core.excepciones.manejador_excepciones_api",
    "DATETIME_FORMAT": "%d-%m-%Y %H:%M",
    "VIEW_NAME_FUNCTION": "core.nombres.nombre_de_vista",
}


# ============================================================
# BLOQUE 10 — JWT (djangorestframework-simplejwt)
# ============================================================
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "TOKEN_TYPE_CLAIM": "token_type",
}


# ============================================================
# BLOQUE 11 — DOCUMENTACIÓN OpenAPI 3 (drf-spectacular)
# La descripción y la matriz de roles se completan a medida que se
# agregan endpoints en cada fase.
# ============================================================
DESCRIPCION_API = f"""
API REST de **{NOMBRE_COMERCIAL}**, plataforma de control de asistencia y
reserva de clases para gimnasios.

**Alumna:** {ALUMNO_NOMBRE}

---

## Cómo autenticarse

1. Ejecute `POST /api/auth/token/` con un usuario y contraseña de prueba.
2. Copie el valor de `access` que devuelve la respuesta.
3. Pulse **Authorize** y pegue el token (esquema *Bearer*).

## Credenciales de prueba

Se crean con `python manage.py seed_data`.
"""

SPECTACULAR_SETTINGS = {
    "TITLE": f"{NOMBRE_COMERCIAL} — API de control de asistencia y reservas",
    "DESCRIPTION": DESCRIPCION_API,
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SORT_OPERATIONS": False,
    "SCHEMA_PATH_PREFIX": "/api",
    "SWAGGER_UI_SETTINGS": {
        "persistAuthorization": True,
        "displayRequestDuration": True,
        "docExpansion": "list",
        "filter": True,
    },
    "CONTACT": {"name": ALUMNO_NOMBRE},
    "LICENSE": {"name": "Uso académico — EVA-3 Desarrollo Backend"},
    "TAGS": [
        {"name": "General", "description": "Raíz de la API."},
    ],
}


# ============================================================
# BLOQUE 12 — LOCALIZACIÓN CHILENA
# ============================================================
LANGUAGE_CODE = "es-cl"
TIME_ZONE = "America/Santiago"
USE_I18N = True
USE_TZ = True


# ============================================================
# BLOQUE 13 — ARCHIVOS ESTÁTICOS Y ALMACENAMIENTO
# ============================================================
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ============================================================
# BLOQUE 14 — MENSAJES FLASH CON CLASES DE BOOTSTRAP
# ============================================================
MESSAGE_TAGS = {
    mensajes.DEBUG: "secondary",
    mensajes.INFO: "info",
    mensajes.SUCCESS: "success",
    mensajes.WARNING: "warning",
    mensajes.ERROR: "danger",
}


# ============================================================
# BLOQUE 15 — AJUSTES EXCLUSIVOS DEL ENTORNO DE PRUEBAS
# PBKDF2 (producción) es lento a propósito; en pruebas se reemplaza
# por un hasher rápido porque se crean e inician sesión con muchos
# usuarios. Solo aplica cuando el proceso es "manage.py test".
# ============================================================
EJECUTANDO_PRUEBAS = "test" in sys.argv

if EJECUTANDO_PRUEBAS:
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


# ============================================================
# BLOQUE 16 — REGISTRO DE ERRORES EN CONSOLA
# ============================================================
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": "[{levelname}] {asctime} {name}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "consola": {"class": "logging.StreamHandler", "formatter": "simple"},
    },
    "root": {"handlers": ["consola"], "level": "WARNING"},
    "loggers": {
        "django.request": {
            "handlers": ["consola"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}
