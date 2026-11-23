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
pip install -e "/ruta/a/EngineDj[postgres]"
pip install "requests>=2.32,<3"   # cliente de Odoo (apps.apiOdoo)
cp .env.example .env
# Edita .env: DATABASE_URL debe apuntar a tu PostgreSQL.
python manage.py migrate
python manage.py seed_hurgo     # roles, permisos, tipos de adjunto y workflows
python manage.py runserver
```

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

Una app por grupo del modelo de datos (HurgoTrack.mwb) más la integración con Odoo.

| App | Grupo | Modelos |
| --- | --- | --- |
| `apps.core` | Base compartida | `M_audit_base`, `M_catalog_base`, campo cifrado, permisos, helpers de steps, `seed_hurgo` |
| `apps.companies` | Empresas y usuarios | `M_company`, `M_user_detail`, `M_user_company`, `M_partner` |
| `apps.locations` | Direcciones | `M_country`, `M_location`, `M_address`, `M_address_attach` |
| `apps.fleet` | Flota | `M_vehicle`, catálogos, `M_soat`, `M_mechanical_inspection`, `M_vehicle_gps`, `M_vehicle_attach` |
| `apps.drivers` | Conductores | `M_driver`, `M_driver_attach` |
| `apps.orders` | Pedidos y productos | `M_type_item`, `M_brand`, `M_item`, `M_order`, `M_order_line`, `M_order_line_trip`, `M_order_event` |
| `apps.trips` | Viajes y entregas | `M_trip`, `M_trip_line`, `M_trip_line_serie`, `M_trip_event`, `M_trip_type_attach`, `M_trip_attach` |
| `apps.apiOdoo` | Integración Odoo | `M_odoo_purchase`, `M_odoo_sync_log` + cliente JSON-RPC |

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
```

Convenciones de modelos: `model_name`, FK `<campo>_id` con `db_column` y
`related_name="<modelo>_<campo>"` (así se navegan las relaciones con
`list.relations`), choices como listas `<campo>_choices`, permisos propios en
`Meta.permissions` (ej. `trips.assign_trip`, `orders.confirm_order`).

## Workflows (API)

Cada acción es un workflow que crea `seed_hurgo`: primero `validate.permission`
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
| – | `orders.items`, `companies.recipients` | Comercial / despacho | `company_id`, `q` |
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
