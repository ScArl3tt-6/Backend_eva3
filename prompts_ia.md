# Evidencia de uso de Inteligencia Artificial — FitLife

**Alumna:** Genesis Quezada Sanzana · **Evaluación:** EVA-3 Desarrollo Backend

Convención: las filas marcadas con ✏️ contienen información que solo yo
puedo completar con exactitud (lo que escribí fuera de esta sesión de
Claude Code, o lo que todavía no ha ocurrido al momento de redactar este
archivo, como el despliegue real en el servidor). Las dejo con una
plantilla para llenar antes de entregar.

## Tabla resumen

| # | Fecha | Herramienta | Objetivo | Archivos afectados |
|---|---|---|---|---|
| 1 ✏️ | ✏️ | Claude (chat web) | Entender el enunciado y la pauta de evaluación | — (análisis, sin código) |
| 2 | 2026-10-26 | Claude Code | Plan completo del proyecto (apps, modelos, reglas, rutas, permisos) | ninguno (solo planificación) |
| 3 | 2026-10-26 | Claude Code | Ajustar 6 reglas de negocio antes de programar | ninguno (acuerdo, se aplicó después) |
| 4 | 2026-10-26 / 27 | Claude Code | Implementar las Fases 1 a 9 (modelos, servicios, API, web, Admin, seed_data) | todo `usuarios/`, `socios/`, `membresias/`, `accesos/`, `clases/`, `core/`, `templates/`, `static/`, `fitlife/settings.py` |
| 5 | 2026-10-28 | Claude Code | Reiniciar la base de datos, correr las migraciones y las pruebas por primera vez, corregir los bugs reales que aparecieron | `accesos/urls.py`, `clases/tests.py`, `accesos/serializers.py`, `accesos/views.py` |
| 6 ✏️ | ✏️ | Claude Code | Apoyo para el despliegue en AWS EC2 | `README.md` (guía), pendiente de validar en el servidor real |

---

## 1. Análisis del enunciado y la pauta — ✏️ COMPLETAR

- **Fecha:** ✏️ _(la fecha en que usaste Claude chat para leer el enunciado y la rúbrica)_
- **Herramienta:** Claude (chat web)
- **Objetivo:** Entender qué pedía el "Proyecto 2: Plataforma de Control de
  Asistencia y Reserva de Clases (FitLife)" y cómo se traduce cada criterio
  de la rúbrica (PostgreSQL, Django Admin, CRUD y reglas, seguridad/IA,
  despliegue) en tareas concretas.
- **Prompt utilizado:** ✏️ _(pega aquí, textual o resumido, lo que le
  escribiste a Claude chat)_
- **Resultado obtenido:** ✏️ _(qué te respondió: por ejemplo, la lista de
  entidades/roles que identificó, o las dudas que te ayudó a resolver)_
- **Qué revisé o corregí yo:** ✏️ _(qué parte de esa respuesta ajustaste
  antes de pedírselo a Claude Code, si corresponde)_
- **Archivos afectados:** ninguno; fue trabajo de análisis, previo a
  escribir código.

---

## 2. Plan completo del proyecto y aprobación

- **Fecha:** 2026-10-26
- **Herramienta:** Claude Code (este asistente, en la carpeta del repositorio)
- **Objetivo:** Traducir el enunciado en un plan concreto antes de escribir
  una sola línea de código: apps de Django, modelos con sus campos y
  relaciones (incluido `on_delete` de cada FK), reglas de negocio de las 4
  funcionalidades, rutas web y de API, y permisos por rol.
- **Prompt utilizado (resumido):** le pedí a Claude Code que primero
  ejecutara `git remote -v`, clonara como referencia (fuera de esta carpeta,
  sin modificarlas) mi proyecto de la EVA-2 (patrón de `settings.py`,
  roles, `servicios.py`, paleta visual) y un segundo repositorio con manejo
  de cupos con `select_for_update`, y que con eso armara el plan completo
  de FitLife y esperara mi aprobación.
- **Resultado obtenido:** un plan con 6 apps (`core`, `usuarios`, `socios`,
  `membresias`, `accesos`, `clases`), el detalle de cada modelo y sus
  restricciones de base de datos, la lógica de negocio de las 4
  funcionalidades, el mapa de rutas web/API y la matriz de permisos por rol.
- **Qué revisé o corregí yo:** pedí 6 ajustes antes de aprobarlo (ver
  entrada 3): una restricción de unicidad más estricta en las membresías,
  un modelo `Instalacion` para el aforo en vez de una variable de entorno,
  reglas más precisas para las reservas, `on_delete=PROTECT` en los
  registros de auditoría en vez de `CASCADE`, la prueba de que el QR
  regenerado invalida el anterior, y usar Python 3.12 en el entorno local.
- **Archivos afectados:** ninguno todavía; el plan se aprobó recién con los
  ajustes de la entrada siguiente.

---

## 3. Ajuste de 6 reglas de negocio antes de programar

- **Fecha:** 2026-10-26
- **Herramienta:** Claude Code
- **Objetivo:** Cerrar seis decisiones de diseño que cambiaban el
  comportamiento del sistema, antes de que se escribiera código que
  hubiera que reescribir después.
- **Prompt utilizado (resumido):** especifiqué que (1) un socio no puede
  tener a la vez más de una membresía ACTIVA o CONGELADA, y que pagar con
  una CONGELADA debe rechazarse con un mensaje claro; (2) el aforo debe
  vivir en un modelo `Instalacion` (no en el `.env`) para poder bloquearlo
  con `select_for_update()`; (3) una reserva exige que la membresía esté
  ACTIVA hoy y que su `fecha_fin` cubra la fecha de la clase, y que
  cancelar una clase cancele también sus reservas activas; (4) `Pago`,
  `RegistroAcceso` y `Reserva` no deben usar `CASCADE` hacia el socio,
  porque los socios y usuarios nunca se borran, solo se desactivan; (5) el
  token QR regenerado debe invalidar de inmediato el anterior, con prueba;
  (6) usar Python 3.12 para el entorno local, igual que el servidor.
- **Resultado obtenido:** Claude Code confirmó que aplicaría cada ajuste
  con su prueba correspondiente y, con eso, empezó a programar desde la
  Fase 1.
- **Qué revisé o corregí yo:** ninguno en este punto; los seis ajustes se
  verificaron más tarde leyendo el código y, sobre todo, corriendo las
  pruebas automatizadas (ver entrada 5).
- **Archivos afectados:** ninguno directamente; quedaron reflejados en
  `membresias/models.py` y `membresias/servicios.py` (ajuste 1),
  `accesos/models.py` y `accesos/servicios.py` (ajuste 2), `clases/servicios.py`
  (ajuste 3), los modelos de `membresias/`, `accesos/` y `clases/` (ajuste 4),
  `socios/models.py` y las pruebas de `accesos/tests.py` (ajuste 5).

---

## 4. Implementación de las Fases 1 a 9

- **Fecha:** 2026-10-26 y 2026-10-27
- **Herramienta:** Claude Code
- **Objetivo:** Escribir el proyecto completo: esqueleto de Django, las
  cinco apps de negocio con sus modelos/servicios/admin/API/vistas web,
  el tema visual, la personalización del Django Admin y el comando
  `seed_data`, avanzando fase por fase sin detenerse a pedir aprobación en
  cada una (instrucción explícita que di para no frenar el avance).
- **Prompt utilizado (resumido):** "avanza por TODAS las fases restantes
  del plan sin detenerte a pedirme aprobación entre fases. Al terminar
  cada fase, ejecuta `check` y `test`, y si pasan, haz un commit local...
  Detente solo si hay un error que no puedas resolver, si necesitas que yo
  escriba algo, o si una decisión cambia algo importante del plan
  aprobado."
- **Resultado obtenido:** el código de las apps `usuarios`, `socios`,
  `membresias`, `accesos` y `clases` (modelos, `servicios.py`, `admin.py`,
  serializers y vistas de API, vistas y plantillas web), el tema visual
  (`static/css/tema.css`, `templates/base.html`, navbar por rol), la
  personalización del Admin, y `seed_data`. Claude Code se detuvo
  correctamente dos veces por la regla "necesito que escribas algo": una
  vez porque la base de datos local quedó con un historial de migraciones
  inconsistente (por haber corrido `migrate` antes de definir
  `AUTH_USER_MODEL`) y pidió autorización para reiniciarla; y otra vez
  porque, sin la base de datos disponible, no podía ejecutar ni una sola
  prueba automatizada para verificar ese código.
- **Qué revisé o corregí yo:** reiniciar `fitlife_db` en el puerto correcto
  de mi PostgreSQL local (tenía dos instancias instaladas) y, en el paso
  siguiente, pedir explícitamente que se corrieran las pruebas y se
  corrigieran los errores reales en vez de simplificarlos (ver entrada 5).
- **Archivos afectados:** prácticamente todo el proyecto; los commits
  "Fase 2" a "Fase 6" del repositorio corresponden uno a uno a esta
  entrada.

---

## 5. Verificación con pruebas reales y corrección de bugs

- **Fecha:** 2026-10-28
- **Herramienta:** Claude Code
- **Objetivo:** Con la base de datos ya disponible, generar las
  migraciones de todas las apps, aplicarlas, y correr por primera vez la
  suite completa de pruebas automatizadas (el código de las Fases 2 a 9
  nunca se había probado realmente). Corregir los errores reales en el
  código, sin debilitar ni borrar pruebas para que "pasaran".
- **Prompt utilizado (resumido):** "Verifica que las migraciones de todas
  las apps estén completas y coherentes... ejecuta `manage.py test` y
  corrige TODOS los errores del código... No debilites ni borres pruebas
  para que pasen: corrige el código. Ejecuta `seed_data` dos veces para
  comprobar que es idempotente. Haz commits locales... Protege
  `/api/docs/` y `/api/schema/` con sesión iniciada (con su prueba)."
- **Resultado obtenido:** 86 pruebas automatizadas, todas aprobadas. Se
  encontraron y corrigieron dos bugs reales:
  1. En `accesos/urls.py`, la ruta `accesos/validar/` estaba declarada
     *después* de las rutas del router de DRF, así que el patrón de
     detalle del router (`accesos/<pk>/`) interpretaba "validar" como un
     `pk` y devolvía `405` en vez de ejecutar `ValidarAccesoView`.
  2. En `clases/tests.py`, la función auxiliar `_crear_instructor()`
     creaba un usuario nuevo con el mismo nombre de usuario por defecto
     cada vez que se llamaba sin indicar instructor, lo que rompía con un
     error de unicidad cuando una misma prueba creaba más de una clase.
  También se agregó la protección por sesión de `/api/docs/`,
  `/api/redoc/` y `/api/schema/`, con sus pruebas, y se corrigieron dos
  advertencias de `drf-spectacular` (vistas sin `serializer_class`).
- **Qué revisé o corregí yo:** pedí explícitamente que no se debilitaran
  las pruebas para hacerlas pasar, y revisé que las correcciones fueran al
  código de producción (el ruteo, no la regla de negocio) y no a los
  criterios de aceptación de las pruebas.
- **Archivos afectados:** `accesos/urls.py`, `clases/tests.py`,
  `accesos/serializers.py`, `accesos/views.py`, `core/views.py`,
  `core/tests.py`, `fitlife/urls.py`, `.env.example`.

---

## 6. Apoyo para el despliegue en AWS EC2 — ✏️ COMPLETAR TRAS DESPLEGAR

- **Fecha:** ✏️ _(fecha en que efectivamente desplegaste en el servidor)_
- **Herramienta:** Claude Code
- **Objetivo:** Obtener instrucciones concretas para desplegar FitLife en
  una instancia EC2 Ubuntu 24.04 detrás de Nginx + Gunicorn + PostgreSQL,
  con HTTPS de Let's Encrypt en `hardpoint-genesis.duckdns.org`
  (IP pública `100.62.227.34`).
- **Prompt utilizado (resumido):** pedí que la Fase de documentación final
  incluyera un `README.md` con la guía de despliegue completa (paquetes,
  base de datos, entorno virtual, `systemd` para Gunicorn, el bloque de
  Nginx con `include proxy_params`, Certbot, y los puertos del grupo de
  seguridad de EC2), además de las variables de entorno exactas que debían
  quedar en el `.env` del servidor.
- **Resultado obtenido:** la sección 5 de `README.md`, con los comandos y
  archivos de configuración (`fitlife.service`, el bloque `server` de
  Nginx) listos para copiar en el servidor.
- **Qué revisé o corregí yo:** ✏️ _(completa aquí qué tuviste que ajustar
  al desplegar de verdad: por ejemplo, rutas distintas, la versión exacta
  de Ubuntu/Nginx que trae la instancia, algún permiso de archivo, el
  resultado real de `certbot`, etc.)_
- **Archivos afectados:** `README.md` (guía). Falta confirmar, una vez
  desplegado, si algo del `.env` del servidor o de la configuración de
  Nginx necesitó ajustarse respecto de lo documentado.

---

## Reflexión

Trabajar con Claude Code de principio a fin obligó a sostener un plan
explícito (apps, modelos, reglas, permisos) *antes* de escribir código, y
a revisarlo contra la pauta punto por punto. Lo más valioso no fue que la
IA escribiera los archivos, sino el ida y vuelta de las seis reglas de
negocio del punto 3: decisiones como "¿qué pasa si alguien paga con la
membresía congelada?" o "¿puede un socio reservar una clase cuya fecha cae
después de que su membresía venza?" son exactamente el tipo de caso límite
que una pauta de evaluación espera que el código cubra, y que es fácil
pasar por alto si uno escribe el modelo y la vista de una sola vez.

La lección más concreta, sin embargo, fue la de la entrada 5: todo el
código de las Fases 2 a 9 se escribió sin poder correr una sola prueba real
(la base de datos quedó bloqueada por un problema de migraciones), y al
habilitarla aparecieron dos bugs genuinos —uno de orden de rutas en Django
y otro de una función auxiliar de prueba que generaba datos duplicados—
que ningún `manage.py check` podía detectar porque ambos solo se manifiestan
en tiempo de ejecución, contra una base de datos real. Confirma algo que ya
sabía de la EVA-2 pero que esta vez viví en carne propia: `check` prueba que
el código *carga*, no que *funcione*; solo la suite de pruebas (y, antes de
eso, decidir no debilitarla para que "pasara") demuestra que la lógica de
negocio hace lo que la pauta exige.
