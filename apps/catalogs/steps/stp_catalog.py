"""Steps de catálogos: POST /api/workflows/sync/<nombre>/."""

from rest_framework import serializers

from enginedj.base.steps.helpers import context_user, results, validate_input
from enginedj.modules.registry import register_module

from apps.catalogs.services import S_catalog


class Sz_catalog_list_in(serializers.Serializer):
    catalog = serializers.CharField(max_length=40)
    company_id = serializers.IntegerField(required=False, allow_null=True)


class Sz_catalog_save_in(serializers.Serializer):
    catalog = serializers.CharField(max_length=40)
    id = serializers.IntegerField(required=False, allow_null=True, help_text="Vacío = crear.")
    company_id = serializers.IntegerField(required=False, allow_null=True)
    name = serializers.CharField(max_length=120)
    symbol = serializers.CharField(max_length=20, required=False, allow_blank=True, help_text="Unidades.")
    official_code = serializers.CharField(max_length=20, required=False, allow_blank=True)
    uses_stock = serializers.BooleanField(required=False)
    is_serialized = serializers.BooleanField(required=False)
    stage = serializers.CharField(max_length=10, required=False)
    applies_to = serializers.CharField(max_length=10, required=False)
    is_required = serializers.BooleanField(required=False)
    has_expiration = serializers.BooleanField(required=False)
    is_active = serializers.BooleanField(required=False)


@register_module("catalogs.available", important=True)
def available(context, params, execution):
    """Catálogos que el usuario puede gestionar (empresa: tipos, unidades, marcas; Hurgo: todos)."""
    return results(S_catalog().available(context_user(context)))


@register_module("catalogs.list", important=True)
def list_catalog(context, params, execution):
    """Registros de un catálogo: la empresa ve los suyos y los comunes."""
    data = validate_input(Sz_catalog_list_in, context)
    return results(S_catalog().list(context_user(context), data["catalog"], data.get("company_id")))


@register_module("catalogs.save", important=True)
def save_catalog(context, params, execution):
    """Crea (sin id) o edita un registro de un catálogo."""
    data = validate_input(Sz_catalog_save_in, context)
    catalog = data.pop("catalog")
    return results(S_catalog().save(context_user(context), catalog, data))
