# hurgotrack

Proyecto Django creado con `enginedj-startproject`.

Usa los entrypoints del motor:

- `enginedj.wsgi.application`
- `enginedj.asgi.application`
- `enginedj.celery.app` (cargada desde `config/celery.py`)

## Instalar

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt   # EngineDj vH0.1.0 (con el core de Hurgo Track) + requests
cp .env.example .env
# Edita .env: DATABASE_URL debe apuntar a tu PostgreSQL.
python manage.py migrate
python manage.py seed_workflows # roles, permisos, tipos de adjunto y workflows (seeds.py de cada app)
python manage.py runserver
```

El core (EngineDj) es otro repositorio y aquí solo entra como dependencia, siempre
en la versión **vH0.1.0**. Este repo no guarda código ni un clon del motor.

Cuando se actualice vH0.1.0 en EngineDj, reinstálalo (pip no lo hace solo porque la
versión del paquete no cambia):

```bash
pip install --force-reinstall --no-deps -r requirements.txt
```

Para probar cambios del core antes de publicarlos, instala en el venv tu clon de
EngineDj, que vive fuera de este repo: `pip install --no-deps -e /ruta/a/EngineDj`.

Requiere PostgreSQL 14 o superior. Si prefieres SQLite para una prueba
rápida, cambia `DATABASE_URL=sqlite:///db.sqlite3` en `.env`.

## Producción

```bash
# WSGI
DJANGO_SETTINGS_MODULE=config.settings.production \
gunicorn enginedj.wsgi:application

# ASGI / WebSockets
DJANGO_SETTINGS_MODULE=config.settings.production \
daphne enginedj.asgi:application

# Celery
DJANGO_SETTINGS_MODULE=config.settings.production \
celery -A config worker -l info

DJANGO_SETTINGS_MODULE=config.settings.production \
celery -A config beat -l info
```

## Apps propias

Crea tus apps dentro de `apps/` y agrégalas a `INSTALLED_APPS` en
`config/settings/base.py`.

Si una app registra pasos de workflow, hazlo en su `AppConfig.ready()`:

```python
from django.apps import AppConfig


class MiAppConfig(AppConfig):
    name = "apps.mi_app"

    def ready(self):
        import apps.mi_app.steps  # noqa
```

## Apps de Hurgo Track

Una app por grupo del modelo de datos (HurgoTrack.mwb) más las integraciones con Odoo y Satrack.

El core no es una app de este proyecto: vive en EngineDj, rama **HurgoCore**, en `enginedj.base`.

| Dónde | Qué |
| --- | --- |
| `enginedj.base.models` | `M_model_base` = tabla `base` del .mwb (`company_id`, `create_user`, `update_user`, más código, fechas y `is_active`), `M_catalog_base`, `M_company`, `M_user_company` (`user_has_company`), `M_user_detail` |
| `enginedj.base.entity` | `E_model_base`, `E_company`, `E_user_company`, `E_user_detail` |
| `enginedj.base.repository` | `R_company`, `R_user_company` |
| `enginedj.base.choices` | tipos de documento y categorías de licencia (`license_covers`) |
| `enginedj.base.exceptions` | `BusinessError`, `BusinessPermissionError`, `BusinessNotFound` |
| `enginedj.base.services.permissions` | `has_perm`, `require_perm`, `user_company_ids` |
| `enginedj.base.steps.helpers` | `context_user`, `context_files`, `validate_input`, `validate_files`, `results` |
| `enginedj.base.serializers.sz_common` | `person`, `Sz_position_in`, `Sz_reason_in` |
| `enginedj.base.cache` | `invalidate_apps`, `InvalidateAppsMixin` |
| `enginedj.base.fields` | `EncryptedTextField` (credenciales GPS) |
| `enginedj.workflows` | comando `seed_workflows` |

Apps de este proyecto (`apps/`):

| App | Grupo | Modelos |
| --- | --- | --- |
| `apps.locations` | Direcciones | `M_country`, `M_location`, `M_address`, `M_address_attach` |
| `apps.fleet` | Flota | `M_partner` (propietario), `M_vehicle`, catálogos, `M_soat`, `M_mechanical_inspection`, `M_vehicle_gps`, `M_vehicle_attach` |
| `apps.drivers` | Conductores | `M_driver`, `M_driver_attach` |
| `apps.orders` | Pedidos y productos | `M_type_item`, `M_brand`, `M_item`, `M_order`, `M_order_line`, `M_order_line_trip`, `M_order_event` |
| `apps.trips` | Viajes y entregas | `M_trip`, `M_trip_line`, `M_trip_line_serie`, `M_trip_event`, `M_trip_type_attach`, `M_trip_attach` |
| `apps.apiOdoo` | Integración Odoo | `M_odoo_purchase`, `M_odoo_sync_log` + cliente JSON-RPC |
| `apps.apiSatrack` | Integración Satrack (GPS / mapa) | sin modelos: cliente Keycloak + GraphQL y datos para mapcn |

### Organización (igual que arquitecturabase)

```
apps/<app>/
  models/<modelo>.py        M_<modelo>  (un archivo por modelo; __init__ con "from .x import *")
  entity/E_<modelo>.py      E_<modelo>  (entidad del motor)
  repository/R_<modelo>.py  R_<modelo>(BaseRepositoryImpl): consultas y escrituras al ORM
  services/S_<modelo>.py    S_<modelo>(BaseService): reglas de negocio
  steps/stp_<modelo>.py     @register_module("app.accion"): entrada desde los workflows
  serializers/sz_<app>.py   salida (DRF) y validación de entrada
  views/, urls.py           vacíos: todo se expone por workflows
  apps.py                   ready() importa los steps
  seeds.py                  ROLES, WORKFLOWS y seed() de la app (los lee seed_workflows)
```

`apps/testing.py` tiene el escenario compartido de las pruebas (`build_world`, `run_workflow`).

Convenciones de modelos: `model_name`, FK `<campo>_id` con `db_column` y
`related_name="<modelo>_<campo>"` (así se navegan las relaciones con
`list.relations`), choices como listas `<campo>_choices`, permisos propios en
`Meta.permissions` (ej. `trips.assign_trip`, `orders.confirm_order`).

## Workflows (API)

Cada acción es un workflow que crea `seed_workflows` desde el `seeds.py` de cada app: primero `validate.permission`
y luego el step. El frontend los llama con:

```
POST /api/workflows/sync/<nombre>/      JSON, o multipart con "files" para fotos
→ {"success": true, "details": {"context": {"results": ...}}}
→ {"success": false, "details": {"reason": "module <step> failed: <mensaje>"}}
```

| Paso | Workflow | Quién | Datos |
| --- | --- | --- | --- |
| 1 | `orders.create` | Comercial | `address_id` (cargue), `lines[{item_id, qty, recipient_id, address_id}]`, `submit` |
| 1 | `orders.update`, `orders.submit` | Comercial | `order_id` + datos del pedido |
| 2 | `orders.confirm` | Despacho | `order_id`, `odoo_purchase` |
| – | `orders.cancel` | Comercial / despacho | `order_id`, `reason` |
| – | `orders.retrieve`, `orders.list` | Comercial / despacho | `order_id` / `data{fields, relations, filters...}` |
| – | `orders.items`, `locations.recipients` | Comercial / despacho | `company_id`, `q` |
| 3 | `orders.pending_lines` | Despacho | `company_id` |
| 3 | `trips.build`, `trips.add_allocations` | Despacho | `company_id`, `origin_address_id`, `allocations[{order_line_id, qty}]` |
| 3 | `trips.register_series` | Despacho | `trip_id`, `trip_line_id`, `series[{order_line_trip_id, vin}]` |
| 3 | `trips.assign`, `trips.cancel` | Despacho | `trip_id`, `vehicle_id`, `driver_id` / `reason` |
| 4 | `trips.mine`, `trips.depart` | Conductor | `trip_id`, `latitude`, `longitude` |
| 5 | `trips.start_delivery` | Conductor | `trip_id`, `trip_line_id` |
| 6 | `trips.report_novelty` | Conductor / despacho | `trip_id`, `name`, `description`, `files` |
| 7 | `trips.deliver` | Solo el conductor asignado | `trip_id`, `trip_line_id`, `rating`, `comment`, `files` (remisión firmada) |
| 7 | `trips.register_return`, `trips.create_return_trip` | Conductor / despacho | `trip_id`, `trip_line_id`, `reason` |
| 8 | (automático) | Sistema | el viaje se cierra al entregar o devolver todas las paradas |
| – | `trips.retrieve`, `trips.list` | Según rol | `trip_id` / `data{...}` |
| – | `fleet.document_expirations` | Despacho / admin | `days` |

Roles (grupos): `comercial`, `despacho`, `conductor`, `administracion`. Un
usuario ve las empresas que tenga en `M_user_company`; despacho ve todo
(`view_all_trip`, `view_all_order`).

Autenticación: solo por cookies, la del motor (web y app móvil).
`POST /api/auth/token/` con `username` y `password` deja las cookies httpOnly
`access_token` y `refresh_token`; `POST /api/auth/token/refresh/` renueva el
acceso y `POST /api/auth/logout/` cierra la sesión. El cliente debe enviar las
cookies en cada llamada (`credentials: "include"` en el navegador; un cookie jar
en la app móvil). No se acepta `Authorization: Bearer`.

En local (`config/settings/local.py`) las cookies van sin `Secure` y con
`SameSite=Lax` para que funcionen por http, también desde el emulador y el teléfono.
En producción van `Secure` + `SameSite=None` (https obligatorio).

### App móvil del conductor (`../apk`)

La app usa `POST /api/auth/token/`, `GET /api/auth/user/` (debe tener
`trips.drive_trip`) y los workflows `trips.mine`, `trips.retrieve` y
`trips.depart`. `trips.mine` trae el resumen de paradas para la tarjeta
(`origin_location`, `destination`, `stops_total`, `stops_done`, `total_qty`).

Para que el emulador o el teléfono lleguen al backend, levántalo en todas las
interfaces:

```bash
python manage.py runserver 0.0.0.0:8000
```

- Emulador Android: `10.0.2.2:8000` llega al localhost de Windows y de ahí a WSL.
- Teléfono físico: WSL2 en modo NAT no recibe conexiones por la IP de la red de
  Windows. Activa `networkingMode=mirrored` en `%UserProfile%\.wslconfig`
  (sección `[wsl2]`, luego `wsl --shutdown`), o reenvía el puerto con
  `netsh interface portproxy` (PowerShell como administrador) y abre el puerto
  8000 en el firewall.

## Integración con Odoo (`apps.apiOdoo`)

Odoo sigue llevando la compra, el recibo y la factura; Hurgo Track lleva la logística.

| Workflow / tarea | Qué hace |
| --- | --- |
| `orders.confirm` (con `ODOO_ENABLED=True`) | Valida que la compra exista en Odoo y esté confirmada (`ODOO_CONFIRMED_PURCHASE_STATES`) |
| `apiOdoo.get_purchase` | Trae una compra (purchase.order) y actualiza `M_odoo_purchase` |
| `apiOdoo.get_create_partners` | Crea / actualiza empresas desde res.partner (por NIT y `odoo_ref`) |
| `apiOdoo.get_create_products` | Crea / actualiza productos de una empresa desde product.product |
| Tarea `apiOdoo.tasks.notify_order_delivered` | Al entregarse un pedido deja la nota en la compra de Odoo (reintenta si Odoo no responde) |

Cada llamada queda en `M_odoo_sync_log`. Variables en `.env`:

```
ODOO_ENABLED=False
ODOO_URL=https://mi-empresa.odoo.com
ODOO_DB=
ODOO_USERNAME=
ODOO_API_KEY=
```

## Integración con Satrack (`apps.apiSatrack`)

Posiciones GPS de los vehículos para el mapa del frontend (componentes de
[mapcn](https://www.mapcn.dev): `MapArc`, `MapMarker`, `MapRoute`). La doc de
Satrack está en https://developer.satrack.com:

- Token: `POST https://externalsecurityapi.satrack.com/api/v1/Keycloak/authenticate`
  (multipart, `Grant_type` `password` o `client_credentials`). Se guarda en caché
  hasta poco antes de vencer y se renueva solo si Satrack responde 401.
- Posiciones: `POST https://locationintegrationapi.satrack.com/api/location` con
  GraphQL `last(serviceCodes: [placas])` y `byDate(...)` (máximo 5 días atrás).

Para activarla basta con poner las credenciales en `.env`:

```
SATRACK_ENABLED=True
SATRACK_CLIENT_ID=
# Con usuario (grant password):
SATRACK_USERNAME=
SATRACK_PASSWORD=
# O sin usuario (grant client_credentials):
SATRACK_CLIENT_SECRET=
```

Un vehículo con `M_vehicle_gps` de operador "Satrack" y credenciales propias usa
las suyas (`username` / `password`, `api_key` = client id, `api_secret` = client
secret); si el operador es otro, no se consulta en Satrack. El serviceCode es la
placa (`abc-123` se envía como `ABC123`).

| Workflow | Permiso | Qué devuelve |
| --- | --- | --- |
| `apiSatrack.positions` | `fleet.view_m_vehicle` | `vehicles`: última posición de la flota (o de `vehicle_ids` / `plates`) |
| `apiSatrack.history` | `fleet.view_m_vehicle` | `coordinates` y `points` de un vehículo entre `start` y `end` (por defecto, las últimas 2 h) |
| `apiSatrack.map_overview` | `trips.view_m_trip` | Viajes asignados / en camino / en reparto que el usuario puede ver: `arcs`, `origins`, `stops`, `vehicles` |
| `apiSatrack.trip_map` | `trips.view_m_trip` | Un viaje (`trip_id`): `arcs`, `stops`, `vehicle` y `route` recorrida desde la salida |

Todas las coordenadas van en `[lng, lat]`, el orden de mapcn / MapLibre: los arcos
traen `from` / `to` y los marcadores `longitude` / `latitude`. `arc_mode`: `legs`
(origen → parada 1 → parada 2…, por defecto) o `hub` (origen → cada parada). Las
direcciones sin coordenadas salen en `missing_coordinates`. Si Satrack falla o está
apagado, el mapa sigue con origen y paradas y el error sale en `satrack.errors`.
La última posición se reutiliza `SATRACK_POSITIONS_CACHE_SECONDS` (30 s), así el
frontend puede refrescar el mapa seguido.

## Celery

- Desarrollo: `CELERY_TASK_ALWAYS_EAGER=True` en `local.py`, las tareas corren sin worker.
- Worker real: Redis en `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND=django-db` y
  comentar el modo eager en `local.py`.
- Beat usa `django_celery_beat` (editable en el admin). `fleet.tasks.check_document_expirations`
  corre a diario a las 6:00.

## Pruebas

```bash
DATABASE_URL=sqlite:///test.sqlite3 python manage.py test apps
```
