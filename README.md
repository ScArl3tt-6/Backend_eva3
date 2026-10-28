# FitLife — Plataforma de Control de Asistencia y Reserva de Clases

Proyecto de la Evaluación 3 de Desarrollo Backend (INACAP). Resuelve los tres
problemas del centro deportivo FitLife: congestión en el acceso, sobrecupo en
clases grupales e ingreso de socios con membresías vencidas.

**Alumna:** Genesis Quezada Sanzana

## 1. Funcionalidades

1. **Planes, pagos y estados de membresía** (ACTIVA / VENCIDA / CONGELADA):
   registrar un pago activa o renueva la membresía en la misma transacción.
2. **Validación de acceso por código QR**: antipassback, aforo máximo y
   verificación de membresía en tiempo real; todo intento queda registrado.
3. **Reserva de clases grupales** con cupos y lista de espera FIFO: al
   cancelar una reserva confirmada, se promueve automáticamente a la primera
   persona en espera.
4. **Dashboard de aforo en tiempo real**: la pantalla se actualiza sola cada
   5 segundos (sin recargar) consultando la API.

## 2. Stack tecnológico

- Python 3.12, Django 5.2 (LTS)
- Django REST Framework + djangorestframework-simplejwt (JWT)
- drf-spectacular (OpenAPI 3 / Swagger / ReDoc)
- PostgreSQL (psycopg 3) — único motor soportado
- python-decouple (variables de entorno)
- qrcode (códigos QR en SVG, sin depender de Pillow)
- Gunicorn + Nginx (producción)
- Zona horaria `America/Santiago`, idioma `es-cl`

## 3. Cómo ejecutar en local (Windows / PowerShell)

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

# Cree la base de datos y el usuario en su PostgreSQL local (ajuste el puerto
# al que realmente use su instalación: ver la nota en .env.example).
# psql -U postgres -h localhost -p 5432 -c "CREATE USER fitlife_user WITH PASSWORD 'su_clave' CREATEDB;"
# psql -U postgres -h localhost -p 5432 -c "CREATE DATABASE fitlife_db OWNER fitlife_user;"

copy .env.example .env
# Edite .env: complete SECRET_KEY, DB_PASSWORD y el DB_PORT real de su PostgreSQL.

python manage.py migrate
python manage.py seed_data
python manage.py test
python manage.py runserver
```

Abra `http://127.0.0.1:8000/` (portada pública) o inicie sesión en
`http://127.0.0.1:8000/cuentas/login/`. La API está en `/api/` y su
documentación interactiva en `/api/docs/` (exige sesión iniciada).

## 4. Variables de entorno

Ver `.env.example`, que trae comentada la explicación de cada una y, en un
bloque aparte, los valores que van en el `.env` del servidor. Resumen:

| Variable | Qué hace |
|---|---|
| `SECRET_KEY` | Clave de Django. Obligatoria, sin valor por omisión. |
| `DEBUG` | `False` en producción. |
| `ALLOWED_HOSTS` | Dominios/IP permitidos (coma-separados). |
| `DETRAS_DE_PROXY_HTTPS` | `True` en el servidor: Nginx hace HTTPS y reenvía por HTTP a Gunicorn. |
| `CSRF_TRUSTED_ORIGINS` | Origen HTTPS del sitio en producción. |
| `DB_ENGINE`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | Conexión a PostgreSQL. |
| `SESSION_COOKIE_AGE` | Duración de la sesión web, en segundos. |
| `CONGELAMIENTO_DIAS_MIN` / `MAX` | Rango permitido para congelar una membresía. |
| `CANCELACION_MINUTOS_LIMITE` | Minutos mínimos de anticipación para cancelar una reserva. |
| `ALUMNO_NOMBRE`, `NOMBRE_COMERCIAL` | Aparecen en el footer y en la documentación de la API. |

El aforo máximo del gimnasio **no** es una variable de entorno: vive en la
base de datos (`accesos.Instalacion`, una sola fila, editable desde el
Django Admin), porque la validación de acceso necesita bloquear esa fila con
`select_for_update()` para que dos entradas simultáneas nunca superen el
aforo.

## 5. Despliegue en AWS EC2 (Ubuntu 24.04)

Arquitectura: `navegador → Nginx (HTTPS/Let's Encrypt) → Gunicorn (socket
Unix) → Django → PostgreSQL`.

- **IP pública:** `100.62.227.34`
- **URL:** `https://hardpoint-genesis.duckdns.org`

### 5.1 Paquetes del sistema

```bash
sudo apt update && sudo apt install -y python3.12 python3.12-venv \
  postgresql postgresql-contrib nginx certbot python3-certbot-nginx git
```

### 5.2 Base de datos

```bash
sudo -u postgres psql -c "CREATE USER fitlife_user WITH PASSWORD 'una_clave_fuerte';"
sudo -u postgres psql -c "CREATE DATABASE fitlife_db OWNER fitlife_user;"
```

### 5.3 Proyecto y entorno virtual

```bash
cd /opt
sudo git clone https://github.com/ScArl3tt-6/Backend_eva3.git fitlife
cd fitlife
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

cp .env.example .env
nano .env   # complete con los valores del bloque "SOLO PARA EL SERVIDOR"

python manage.py migrate
python manage.py seed_data        # datos de demostración (opcional en producción real)
python manage.py collectstatic --noinput
python manage.py check --deploy   # debe quedar solo con advertencias aceptadas (ver GUIA_DEFENSA.md)
```

### 5.4 Gunicorn como servicio systemd

`/etc/systemd/system/fitlife.service`:

```ini
[Unit]
Description=Gunicorn de FitLife
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/opt/fitlife
EnvironmentFile=/opt/fitlife/.env
ExecStart=/opt/fitlife/.venv/bin/gunicorn fitlife.wsgi:application \
  --bind unix:/opt/fitlife/fitlife.sock --workers 3

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now fitlife
```

### 5.5 Nginx

`/etc/nginx/sites-available/fitlife`:

```nginx
server {
    listen 80;
    server_name hardpoint-genesis.duckdns.org;

    location /static/ {
        alias /opt/fitlife/staticfiles/;
    }
    location /media/ {
        alias /opt/fitlife/media/;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/opt/fitlife/fitlife.sock;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/fitlife /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d hardpoint-genesis.duckdns.org
```

`include proxy_params` es justamente lo que le agrega a cada petición el
encabezado `X-Forwarded-Proto`; por eso `DETRAS_DE_PROXY_HTTPS=True` en el
`.env` del servidor es imprescindible: sin él, Django no sabría que la
conexión original del navegador fue HTTPS y las cookies "Secure" fallarían.

### 5.6 Grupos de seguridad de EC2

Puertos abiertos: 22 (SSH, solo desde su IP), 80 y 443 (HTTP/HTTPS, desde
cualquier IP). El puerto de PostgreSQL (5432) **no** se expone a Internet.

## 6. Credenciales de demostración

Se crean con `python manage.py seed_data` (idempotente: se puede correr
varias veces sin duplicar nada).

| Usuario | Contraseña | Rol |
|---|---|---|
| `admin` | `Admin.2026` | Administrador (también entra a `/admin/`) |
| `recepcion1` | `Recepcion.2026` | Recepción |
| `instructor1` / `instructor2` | `Instructor.2026` | Instructor |
| `socio1` … `socio4` | `Socio.2026` | Socio, membresía **ACTIVA** |
| `socio5` / `socio6` | `Socio.2026` | Socio, membresía **VENCIDA** |
| `socio7` / `socio8` | `Socio.2026` | Socio, membresía **CONGELADA** |

El comando imprime, al final, el token QR de `socio1` (activo, para probar
un acceso permitido) y de `socio5` (vencido, para probar uno denegado).

## 7. Cómo correr las pruebas

```powershell
python manage.py test
```

Incluye pruebas de reglas de negocio (pagos, congelamiento, cupos, lista de
espera, antipassback, aforo), de restricciones de la base de datos, de
permisos por rol y por objeto (un socio nunca ve datos de otro, ni por la
web ni por la API), y una prueba de concurrencia real con hilos para el
aforo.

## 8. Documentación adicional

- `prompts_ia.md`: evidencia estructurada del uso de IA durante el desarrollo.
- `GUIA_DEFENSA.md`: arquitectura explicada, mapa de la pauta a archivos
  concretos, guion de demostración en vivo y preguntas de defensa.
