from enginedj.base.steps.helpers import context_user, results, validate_input
from enginedj.modules.registry import register_module

from apps.locations.serializers import (
    Sz_company_address,
    Sz_company_address_in,
    Sz_company_id_in,
    Sz_loading_point,
    Sz_loading_point_in,
    Sz_loading_points_in,
    Sz_loading_tag,
    Sz_tag_in,
    Sz_tags_in,
)
from apps.companies.tenancy import company_schema, in_company_schema
from apps.locations.services import S_address


@register_module("locations.loading_points", important=True)
def loading_points(context, params, execution):
    """Lugares de cargue (centrales). Filtros: company_id (dueña), tag_ids, q. Con order_id + order_company_id
    (o item_ids) sugiere los que tienen las etiquetas de esos productos y los pone primero."""
    user = context_user(context)
    data = validate_input(Sz_loading_points_in, context)

    def run():
        return S_address().loading_points(user, company_id=data.get("company_id"), tag_ids=data["tag_ids"],
                                          item_ids=data["item_ids"], order_id=data.get("order_id"), query=data["q"])

    if data.get("order_id") or data["item_ids"]:
        # Los productos viven en el esquema de la empresa del pedido
        with company_schema(data.get("order_company_id"), user):
            points = run()
    else:
        points = run()
    return results(Sz_loading_point(points, many=True).data)


@register_module("locations.loading_point.save", important=True)
def save_loading_point(context, params, execution):
    """Crea (sin address_id) o actualiza un lugar de cargue con sus etiquetas (tag_ids)."""
    data = validate_input(Sz_loading_point_in, context)
    address = S_address().save_loading_point(context_user(context), data)
    return results(Sz_loading_point(address).data)


@register_module("locations.loading_tags", important=True)
def loading_tags(context, params, execution):
    """Catálogo de etiquetas de cargue. Filtro opcional: q."""
    data = validate_input(Sz_tags_in, context)
    return results(Sz_loading_tag(S_address().tags(context_user(context), data["q"]), many=True).data)


@register_module("locations.loading_tag.create", important=True)
def create_loading_tag(context, params, execution):
    data = validate_input(Sz_tag_in, context)
    return results(Sz_loading_tag(S_address().create_tag(context_user(context), data["name"])).data)


@register_module("locations.lookups", important=True)
def lookups(context, params, execution):
    """Listas para los formularios de Hurgo: empresas activas (con su rol) y municipios."""
    return results(S_address().lookups(context_user(context)))


@register_module("locations.addresses", important=True)
@in_company_schema()
def company_addresses(context, params, execution):
    """Direcciones de una empresa: las de entrega y bodegas que ella guarda. Sin company_id = la del usuario."""
    data = validate_input(Sz_company_id_in, context)
    return results(Sz_company_address(S_address().company_addresses(context_user(context), context["company_id"]),
                                      many=True).data)


@register_module("locations.address.save", important=True)
@in_company_schema()
def save_company_address(context, params, execution):
    """Crea (sin address_id) o edita una dirección de la empresa."""
    data = validate_input(Sz_company_address_in, context)
    return results(Sz_company_address(S_address().save_company_address(context_user(context), data)).data)
