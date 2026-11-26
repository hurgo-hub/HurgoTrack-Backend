"""Acceso al esquema de PostgreSQL de cada empresa.

- ``create_company_schema(company)``: al dar de alta la empresa (crea el esquema ``c<id>`` y sus tablas).
- ``company_schema(company_id, user=None)``: entra al esquema de la empresa (``search_path = c<id>, public``).
  Con ``user``, valida que sea de esa empresa o de Hurgo: un usuario de empresa nunca entra a otro esquema.
- ``in_company_schema(...)``: decorador de steps; el step completo corre en el esquema de la empresa
  (``company_id`` del input o la empresa del usuario; para viajes, la empresa del viaje).
- ``for_each_company(fn)``: Hurgo recorre los esquemas de las empresas activas (listados de varias empresas).
"""

from contextlib import contextmanager
from functools import wraps

from django_tenants.utils import schema_context

from enginedj.base.exceptions import BusinessError, BusinessNotFound, BusinessPermissionError
from enginedj.base.services.permissions import user_company_ids

# Permisos que solo tiene el equipo de Hurgo (despacho, administración, conductores)
HURGO_PERMS = ("orders.view_all_order", "companies.create_company", "trips.build_trip", "stock.view_all_stock",
               "trips.drive_trip")


def schema_name_for(company_id) -> str:
    return f"c{int(company_id)}"


def create_company_schema(company):
    from django.db import connection

    from apps.companies.models import M_tenant

    tenant = M_tenant.objects.filter(company=company).first()
    if tenant is None:
        tenant = M_tenant(company=company, schema_name=schema_name_for(company.pk))
        # Las FK de Django son diferidas: si en esta transacción ya hay filas recién creadas (la
        # propia empresa), PostgreSQL no deja crear FK hacia esas tablas ("pending trigger events").
        # Se validan ya y se vuelven a diferir al terminar.
        with connection.cursor() as cursor:
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
        try:
            tenant.save(verbosity=0)  # crea el esquema y corre sus migraciones
        finally:
            with connection.cursor() as cursor:
                cursor.execute("SET CONSTRAINTS ALL DEFERRED")
    return tenant


def is_hurgo(user) -> bool:
    """Usuario de Hurgo: tiene permisos de Hurgo y no pertenece a ninguna empresa."""
    if user is None or not user.is_authenticated:
        return False
    return (user.is_superuser or any(user.has_perm(p) for p in HURGO_PERMS)) and not user_company_ids(user)


def tenant_schema(company_id) -> str:
    from apps.companies.models import M_tenant

    tenant = M_tenant.objects.filter(company_id=company_id).only("schema_name").first()
    if tenant is None:
        raise BusinessNotFound("La empresa no tiene esquema de datos.")
    return tenant.schema_name


def resolve_company(user, company_id=None) -> int:
    """Empresa sobre la que se trabaja: la indicada (Hurgo, o la propia) o la única del usuario."""
    own = user_company_ids(user) if user is not None else []
    if company_id in (None, ""):
        if len(own) == 1:
            return own[0]
        raise BusinessError("Indica la empresa.", code="company_required")
    company_id = int(company_id)
    if company_id not in own and not is_hurgo(user):
        raise BusinessPermissionError("Solo puedes acceder a los datos de tu empresa.")
    return company_id


@contextmanager
def company_schema(company_id, user=None):
    if user is not None:
        company_id = resolve_company(user, company_id)
    with schema_context(tenant_schema(company_id)):
        yield company_id


def for_each_company(fn, company_ids=None):
    """Llama ``fn(company_id)`` dentro del esquema de cada empresa con esquema y junta los resultados."""
    from apps.companies.models import M_tenant

    tenants = M_tenant.objects.filter(company__is_active=True).order_by("company_id")
    if company_ids is not None:
        tenants = tenants.filter(company_id__in=company_ids)
    out = []
    for tenant in tenants:
        with schema_context(tenant.schema_name):
            out.extend(fn(tenant.company_id))
    return out


def _context_user(context):
    from enginedj.base.steps.helpers import context_user

    return context_user(context)


def in_company_schema(company_from=None, optional=False):
    """Decorador de steps: corre el step en el esquema de la empresa.

    ``company_from(context, user)`` devuelve la empresa (por defecto ``company_id`` del input o la del
    usuario). Con ``optional=True``, si no hay empresa (Hurgo sin ``company_id``) el step corre en el
    esquema central (ej. listados que recorren todas las empresas).
    """

    def decorator(step):
        @wraps(step)
        def wrapper(context, params, execution):
            user = _context_user(context)
            raw = company_from(context, user) if company_from else context.get("company_id")
            if raw in (None, "") and optional and is_hurgo(user):
                return step(context, params, execution)
            company_id = resolve_company(user, raw)
            context["company_id"] = company_id
            with schema_context(tenant_schema(company_id)):
                return step(context, params, execution)

        return wrapper

    return decorator


def trip_company(context, user):
    """Empresa de un viaje (``trip_id`` del input): el step corre en el esquema de esa empresa."""
    from apps.trips.models import M_trip

    trip_id = context.get("trip_id")
    company_id = M_trip.objects.filter(pk=trip_id).values_list("company_id", flat=True).first() if trip_id else None
    if company_id is None or (not is_hurgo(user) and company_id not in user_company_ids(user)):
        raise BusinessNotFound("El viaje no existe.")  # a otra empresa ni se le confirma que existe
    return company_id
