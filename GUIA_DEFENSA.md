# Guía de Defensa — FitLife

Documento de apoyo para la defensa en vivo: arquitectura, mapa de la pauta
a archivos concretos, guion de demostración y preguntas probables.

## 1. Arquitectura, explicada simple

```
Navegador  →  Nginx (HTTPS, puerto 443)  →  Gunicorn (socket Unix)  →  Django  →  PostgreSQL
             certificado Let's Encrypt       3 workers                 WSGI       fitlife_db
```

- **Nginx** es la puerta de entrada pública: atiende HTTPS con el
  certificado de Let's Encrypt, sirve los archivos estáticos directamente
  (`/static/`, `/media/`) y reenvía todo lo demás a Gunicorn por un socket
  Unix. También agrega el encabezado `X-Forwarded-Proto: https` (con
  `include proxy_params`), para que Django sepa que la conexión original
  fue segura aunque internamente viaje por HTTP.
- **Gunicorn** es el servidor WSGI que de verdad ejecuta el código Python
  de Django; corre como un servicio `systemd` (`fitlife.service`) con 3
  procesos ("workers"), para atender varias peticiones a la vez.
- **Django** resuelve la URL, aplica los permisos, llama a `servicios.py`
  para la lógica de negocio y usa el ORM para leer/escribir en PostgreSQL.
- **PostgreSQL** es la única base de datos del proyecto: todas las
  relaciones (socio → membresía → pago, clase → reserva, etc.) y las
  restricciones (`UniqueConstraint`, `CheckConstraint`) viven ahí, no en
  Python.

El dominio público es `hardpoint-genesis.duckdns.org` (IP `100.62.227.34`).

## 2. Mapa de la pauta a archivos concretos

### Criterio 1 — PostgreSQL

- Conexión íntegra por variables de entorno: `fitlife/settings.py`
  (bloque 7), leídas con `python-decouple` desde `.env` (nunca hay un
  secreto escrito a mano en el código).
- Migraciones limpias: una app por carpeta `migrations/`; `makemigrations
  --check` no reporta cambios pendientes.
- Relaciones: `ForeignKey`/`OneToOneField` en todos los modelos de
  `socios/models.py`, `membresias/models.py`, `accesos/models.py`,
  `clases/models.py`, cada uno con su `on_delete` pensado (ver sección 4).
- Restricciones en la base de datos:
  - `membresias/models.py` → `UniqueConstraint` de una sola membresía
    ACTIVA o CONGELADA por socio.
  - `clases/models.py` → `UniqueConstraint` de una sola reserva activa por
    socio y clase; `CheckConstraint` de `cupo_maximo > 0`.
  - `membresias/models.py` → `CheckConstraint` de `precio > 0` y
    `monto > 0`.
  - `accesos/models.py` → `CheckConstraint` de `aforo_maximo > 0`.

### Criterio 2 — Django Admin

- Todos los modelos registrados: `usuarios/admin.py`, `socios/admin.py`,
  `membresias/admin.py`, `accesos/admin.py`, `clases/admin.py`.
- `list_display`, `list_filter`, `search_fields`, `date_hierarchy` en cada
  `ModelAdmin`.
- Inlines: membresías y pagos dentro del socio (`socios/admin.py`,
  `SocioAdmin.inlines`), reservas dentro de la clase
  (`clases/admin.py`, `ClaseAdmin.inlines`).
- `readonly_fields` de auditoría y `has_add_permission`/
  `has_delete_permission` en `False` para `Pago` y `RegistroAcceso`
  (son evidencia, no se editan ni se borran).
- Acciones masivas: congelar/descongelar (`membresias/admin.py`,
  `accion_descongelar`), marcar asistencia (`clases/admin.py`,
  `accion_marcar_asistio`/`accion_marcar_no_asistio`), cancelar clase.
- Insignias de color con `format_html`: función `_insignia_estado`/
  `_insignia` en cada `admin.py`.
- Plantilla propia: `templates/admin/base_site.html` +
  `static/css/admin_fitlife.css`; `site_header`/`site_title`/`index_title`
  en español, fijados en `core/apps.py` (método `ready()`).

### Criterio 3 — CRUD y reglas del caso

Toda la lógica de negocio vive en `servicios.py` de cada app (nunca en las
vistas):

- `membresias/servicios.py`: `registrar_pago`, `congelar`, `descongelar`,
  `verificar_vencimiento`, `actualizar_membresias_vencidas`.
- `accesos/servicios.py`: `validar_acceso`, `ocupacion_actual`, `cerrar_dia`.
- `clases/servicios.py`: `reservar_clase`, `cancelar_reserva`,
  `cancelar_clase`, `marcar_asistencia`.

Cada una tiene CRUD web (`views_html.py` + `templates/<app>/`) y CRUD API
(`views.py` + `serializers.py`, bajo `/api/`).

### Criterio 4 — Seguridad, sesiones y apoyo de IA

- Autenticación: `usuarios/urls.py` usa `LoginView`/`LogoutView` de Django
  (el `LogoutView` de Django 4.1+ solo acepta `POST`, tal como exige la
  pauta). Sesión configurable por `SESSION_COOKIE_AGE`.
- Toda la web exige login salvo `core:inicio` y `usuarios:login`
  (`core/utilidades.py`, decorador `requiere_rol`, usado en casi todas
  las vistas de `views_html.py`).
- Permisos por rol: `usuarios/permisos.py` (API) y `requiere_rol()` (web).
- Permisos por objeto: `socios/permisos.py` (`EsPropietarioDelSocio`),
  usado por las API de `membresias`, `accesos` y `clases`; probado en
  `ControlDeAccesoDeObjetoApiTests` de cada app.
- Validadores de contraseña: `AUTH_PASSWORD_VALIDATORS` en `settings.py`.
- Cookies seguras activables por `.env`: `DETRAS_DE_PROXY_HTTPS` (bloque
  3-B de `settings.py`).
- CSRF intacto: todos los formularios usan `{% csrf_token %}`; la API usa
  JWT (sin estado, no necesita CSRF) o sesión.
- El QR no expone datos personales: `accesos/qr.py` codifica solo el UUID
  del `token_qr`; se regenera desde `socios/views_html.py`
  (`regenerar_qr`) y el token anterior queda inválido de inmediato
  (`socios/models.py`, `regenerar_token_qr`).
- `/api/docs/`, `/api/redoc/` y `/api/schema/` exigen sesión iniciada
  (`core/views.py`, vistas `Spectacular*Protegida`).
- `prompts_ia.md`: evidencia de uso de IA, en la raíz del proyecto.

### Criterio 5 — Despliegue y defensa

Ver `README.md`, sección 5, para la guía completa de despliegue
(Nginx + Gunicorn + PostgreSQL en EC2), la IP pública, la URL y las
credenciales de demostración.

## 3. Guion de demostración en vivo

1. **Portada pública** (`/`): mostrar que no exige login.
2. **Login** como `recepcion1` / `Recepcion.2026`.
3. **Panel** (`/panel/`): resumen de ocupación, socios y clases de hoy.
4. **Validar acceso** (`/accesos/validar/`):
   - Escanear o escribir el token QR de **`socio1`** (activo, impreso por
     `seed_data`) con tipo "Entrada" → se permite, queda "dentro".
   - Volver a intentar con el mismo token y tipo "Entrada" → se deniega
     por **antipassback**.
   - Escribir el token de **`socio5`** (vencido) → se deniega por
     **membresía vencida**.
5. **Dashboard de aforo** (`/aforo/`): mostrar que el número de ocupación
   sube/baja solo, sin recargar la página (abrir las herramientas de
   desarrollador y señalar la petición a `/api/aforo/` cada 5 segundos).
6. **Membresías** (`/membresias/`): abrir la de un socio ACTIVA, congelarla
   con, por ejemplo, 10 días; mostrar que `fecha_fin` no cambia pero el
   estado sí; luego descongelarla y mostrar que `fecha_fin` se extendió.
7. **Pagos** (`/pagos/nuevo/`): registrar un pago para un socio con
   membresía VENCIDA y mostrar que queda ACTIVA de nuevo, con una fila
   nueva en el historial.
8. **Clases** (`/clases/`): abrir la clase llena del día (2/2 cupos, 2 en
   espera); iniciar sesión como uno de los socios confirmados y cancelar
   su reserva; recargar como administrador y mostrar que el primero de la
   lista de espera pasó a CONFIRMADA automáticamente.
9. **Django Admin** (`/admin/`) con `admin` / `Admin.2026`: mostrar el
   encabezado con la marca FitLife, el inline de membresías/pagos dentro
   de un socio, y la acción masiva de asistencia dentro de una clase.
10. **Swagger** (`/api/docs/`): mostrar que sin sesión iniciada devuelve
    401, e iniciar sesión para verlo completo.

## 4. 30 preguntas probables de la defensa

1. **¿Por qué `Pago.socio` usa `PROTECT` y no `CASCADE`?**
   Porque un socio nunca se borra (solo se desactiva con
   `is_active=False`); `PROTECT` además evita borrar accidentalmente el
   historial financiero si alguien intentara eliminar la fila.
2. **¿Cómo evitas que dos personas reserven el último cupo a la vez?**
   `reservar_clase()` bloquea la fila de la `Clase` con
   `select_for_update()` antes de contar las reservas confirmadas; la
   segunda petición espera a que la primera termine y recién ahí cuenta
   de nuevo.
3. **¿Por qué el aforo vive en un modelo y no en el `.env`?**
   Porque para evitar la condición de carrera hay que poder bloquear esa
   fila con `select_for_update()`; una variable de entorno no se puede
   bloquear en una transacción de base de datos.
4. **¿Qué pasa si alguien paga mientras su membresía está congelada?**
   `registrar_pago()` lo rechaza con `MembresiaCongeladaError` y un
   mensaje claro: debe descongelarla primero.
5. **¿Cómo se calcula si alguien está "dentro" del gimnasio?**
   Se busca su último `RegistroAcceso` con resultado PERMITIDO; si fue una
   ENTRADA, está dentro (antipassback); si fue una SALIDA o no hay
   ninguno, no lo está.
6. **¿Por qué el token QR no expone el RUT ni el nombre?**
   El SVG solo codifica el UUID (`token_qr`); accesos lo resuelve
   buscando ese UUID en la base, nunca al revés.
7. **¿Qué pasa con el token QR anterior al regenerarlo?**
   Deja de servir de inmediato: `regenerar_token_qr()` le asigna un UUID
   nuevo y lo guarda; el anterior ya no coincide con ningún socio.
8. **¿Cómo decide el sistema si una membresía está vencida?**
   `verificar_vencimiento()` compara `fecha_fin` con la fecha de hoy en
   tiempo real (al acceder o reservar) y el comando `actualizar_membresias`
   lo hace en lote una vez al día; ambos son idempotentes.
9. **¿Por qué una membresía congelada no vence aunque pase su `fecha_fin`?**
   Porque el tiempo congelado no cuenta en contra del socio:
   `verificar_vencimiento()` solo actúa sobre membresías ACTIVA.
10. **¿Qué le impide a un socio reservar una clase cuya fecha es posterior
    al vencimiento de su membresía?**
    `reservar_clase()` exige que `fecha_fin` de la membresía sea igual o
    posterior a la fecha de la clase, no solo que esté activa hoy.
11. **¿Qué ocurre con las reservas si se cancela la clase completa?**
    `cancelar_clase()` cambia el estado de la clase y, en la misma
    transacción, cancela todas las reservas CONFIRMADA y EN_ESPERA.
12. **¿Cómo se reordena la lista de espera al cancelar una reserva?**
    Se guarda la posición que quedó vacía (la de quien canceló, o la de
    quien fue promovido) y se resta 1 a la posición de todos los que
    estaban detrás, en la misma transacción.
13. **¿Por qué `LogoutView` exige `POST`?**
    Por seguridad: un `GET` se puede disparar por accidente (un enlace, un
    prefetch del navegador) y cerraría la sesión sin que la persona lo
    pidiera. Desde Django 4.1, `LogoutView` ya exige `POST` por defecto.
14. **¿Qué diferencia hay entre sesión y JWT en este proyecto?**
    La sesión (cookie) la usan las pantallas web y la Browsable API;
    el JWT lo usa cualquier cliente externo a la API
    (`POST /api/auth/token/`). Ambos están habilitados en
    `DEFAULT_AUTHENTICATION_CLASSES`.
15. **¿Cómo se verifica el rol en la API?**
    Con defensa en profundidad: se compara el rol guardado en la base
    (fuente de verdad) y, si la petición llegó con JWT, también el claim
    `rol` del token (`usuarios/permisos.py`, `_tiene_rol`).
16. **¿Qué es el control de acceso a nivel de objeto y dónde se prueba?**
    Que un socio autenticado no pueda ver ni modificar el recurso de
    otro socio aunque adivine el `id`. Se implementa con
    `EsPropietarioDelSocio` y se prueba en `ControlDeAccesoDeObjetoApiTests`
    de cada app (p. ej. `membresias/tests.py`).
17. **¿Por qué `/api/docs/` exige sesión iniciada?**
    Porque el esquema completo de la API (rutas, campos, hasta los
    nombres de las relaciones) no es información que deba quedar pública.
18. **¿Qué hace `CSRF_TRUSTED_ORIGINS` y por qué hace falta en el servidor?**
    Le dice a Django qué orígenes HTTPS puede confiar para el encabezado
    `Origin` al validar CSRF; sin él, los formularios fallarían detrás de
    un proxy que cambia de HTTP a HTTPS.
19. **¿Qué hace `DETRAS_DE_PROXY_HTTPS`?**
    Activa `SECURE_PROXY_SSL_HEADER`, `SESSION_COOKIE_SECURE` y
    `CSRF_COOKIE_SECURE`: le dice a Django que confíe en el encabezado
    `X-Forwarded-Proto` que agrega Nginx, porque Gunicorn recibe la
    conexión por HTTP aunque el navegador use HTTPS.
20. **¿Por qué el proyecto no usa SQLite?**
    Porque la pauta exige PostgreSQL como motor íntegro, y porque
    `CheckConstraint`/`UniqueConstraint` condicionales necesitan un motor
    que las aplique de verdad a nivel de fila.
21. **¿Cómo se prueba la concurrencia del aforo?**
    Con `TransactionTestCase` (no `TestCase`, que envuelve todo en una
    transacción que nunca se confirma) y dos hilos reales que llaman a
    `validar_acceso()` al mismo tiempo con `aforo_maximo=1`; se comprueba
    que solo una ENTRADA se permite.
22. **¿Qué es idempotente en este proyecto y por qué importa?**
    `seed_data`, `actualizar_membresias` y `validar_acceso` (el registro
    del intento). Importa porque se pueden correr varias veces (o un cron
    diario) sin duplicar datos ni romper una restricción de unicidad.
23. **¿Qué pasa si el monto del pago no coincide con el precio del plan?**
    `registrar_pago()` lanza `MontoInvalidoError` antes de tocar la base;
    no se crea ni el pago ni se modifica la membresía.
24. **¿Por qué `Socio.usuario` es `PROTECT` y no `CASCADE`?**
    Porque "borrar" a una persona en este sistema significa desactivar su
    cuenta (`is_active=False`), nunca eliminar la fila; `PROTECT` hace que
    un intento de `DELETE` directo falle en vez de arrastrar en cascada
    todo el historial del socio.
25. **¿Qué significa `select_for_update()` y qué pasaría sin él?**
    Bloquea la fila elegida hasta que termine la transacción; sin él, dos
    transacciones podrían leer el mismo valor "antes" del cambio y las dos
    decidir que hay cupo, aforo o membresía disponible, causando
    sobrecupo o un aforo inflado.
26. **¿Cómo decide el sistema si una reserva queda CONFIRMADA o EN_ESPERA?**
    Cuenta, bajo bloqueo, cuántas reservas CONFIRMADA tiene ya la clase;
    si son menos que `cupo_maximo`, confirma; si no, calcula la próxima
    posición de la lista de espera y la deja EN_ESPERA.
27. **¿Qué garantiza que nunca haya sobrecupo?**
    La combinación de `select_for_update()` en el servicio y el
    `CheckConstraint`/lógica de conteo: aunque el servicio tuviera un error,
    la restricción de la base es la última barrera.
28. **¿Por qué `Plan`, `Membresia` y `Pago` tienen `CheckConstraint` de
    monto/precio positivo si ya se valida en el formulario/serializer?**
    Porque el formulario y el serializer se pueden saltar (otro cliente de
    la API, un script, el propio Admin); la restricción de la base es la
    que no se puede evitar nunca.
29. **¿Qué pasa si se intenta marcar asistencia antes de que empiece la
    clase?**
    `marcar_asistencia()` lo rechaza con `TransicionInvalidaError`: solo
    se puede marcar después de `clase.inicio`.
30. **¿Por qué `seed_data` crea las membresías vencidas "retrocediendo la
    fecha" en vez de poner el estado a mano?**
    Para que la transición pase por `verificar_vencimiento()` (la función
    real de negocio) y quede su fila de historial, en vez de dejar un
    estado inventado que ninguna regla produciría de verdad.

## 5. Repaso de conceptos (prueba de alternativas)

- **ORM:** capa que traduce clases y objetos de Python a filas y consultas
  SQL (y viceversa), sin escribir SQL a mano. Un `QuerySet` es "perezoso":
  no consulta la base hasta que se itera, se imprime o se evalúa.
- **Migraciones:** archivos versionados que describen, paso a paso, cómo
  llevar el esquema de la base de datos del estado anterior al nuevo.
  `makemigrations` las genera comparando los modelos con el historial;
  `migrate` las aplica.
- **Django Admin:** interfaz de administración autogenerada a partir de
  los modelos registrados; se personaliza con `ModelAdmin` (qué columnas
  mostrar, qué filtrar, qué buscar) sin tocar las plantillas, salvo que se
  quiera un branding propio (como `base_site.html` en este proyecto).
- **Serializers (DRF):** convierten instancias de modelos (u otros datos)
  a JSON y de vuelta, y validan la entrada antes de tocar la base de
  datos; son el equivalente, en la API, de un `ModelForm`.
- **ViewSets y routers:** un `ViewSet` agrupa las operaciones CRUD de un
  recurso en una sola clase; un `router` genera automáticamente las URLs
  (`/recurso/`, `/recurso/<id>/`) a partir de esa clase.
- **Permisos:** clases que deciden si una petición puede proceder.
  `has_permission` se evalúa antes de tocar un objeto concreto (p. ej. "es
  administrador"); `has_object_permission` se evalúa sobre un objeto
  puntual (p. ej. "esta reserva es suya").
- **Sesiones vs. JWT:** la sesión guarda un identificador en una cookie y
  el estado real vive en el servidor (tabla `django_session`); el JWT es
  un token firmado que contiene el estado (incluidos claims como el rol) y
  no necesita que el servidor recuerde nada entre peticiones, a costa de
  que invalidarlo antes de que expire es más difícil (por eso existe la
  lista negra de `token_blacklist`).
- **CSRF:** ataque donde un sitio externo hace que el navegador de la
  víctima envíe, sin que ella se dé cuenta, una petición a un sitio donde
  sí tiene sesión iniciada. Django se defiende exigiendo un token
  (`{% csrf_token %}`) que el atacante no puede adivinar ni leer desde
  otro origen.
- **PostgreSQL:** sistema de gestión de bases de datos relacional, con
  soporte real de transacciones ACID, restricciones a nivel de fila
  (`CHECK`, `UNIQUE` con condición) y bloqueo de filas
  (`SELECT ... FOR UPDATE`), que es justamente lo que este proyecto
  necesita para el aforo y los cupos.
- **Gunicorn:** servidor WSGI que ejecuta la aplicación Django como
  procesos de verdad (workers); no sirve archivos estáticos ni habla HTTPS
  por sí mismo, por eso siempre va detrás de un proxy como Nginx.
- **Nginx:** servidor web y proxy inverso; en este proyecto termina la
  conexión HTTPS, sirve los archivos estáticos directamente (más rápido
  que pedírselo a Django) y reenvía el resto a Gunicorn.
- **EC2:** máquina virtual de AWS donde corre todo el stack (Nginx,
  Gunicorn, PostgreSQL) sobre Ubuntu 24.04.
- **Grupos de seguridad:** el "firewall" de EC2; una lista de reglas de
  entrada/salida por puerto e IP de origen. Este proyecto solo necesita
  22 (SSH), 80 y 443 (HTTP/HTTPS) abiertos hacia Internet; PostgreSQL
  (5432) queda cerrado hacia afuera.
