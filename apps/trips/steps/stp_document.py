"""Documentos del pedido y del viaje (subir y consultar los requeridos por etapa)."""

from rest_framework import serializers

from enginedj.base.steps.helpers import context_files, context_user, results, validate_files, validate_input
from enginedj.modules.registry import register_module

from apps.companies.tenancy import in_company_schema, trip_company

from apps.trips.serializers import validate_attach
from apps.trips.services import S_document


class Sz_order_doc_in(serializers.Serializer):
    order_id = serializers.IntegerField()
    company_id = serializers.IntegerField(required=False, allow_null=True)
    document_key = serializers.CharField(max_length=40, required=False, help_text='"company:<id>"')


class Sz_trip_doc_in(serializers.Serializer):
    trip_id = serializers.IntegerField()
    document_key = serializers.CharField(max_length=40, required=False, help_text='"hurgo:<id>" o "company:<id>"')
    trip_line_id = serializers.IntegerField(required=False, allow_null=True)


@register_module("orders.documents", important=True)
@in_company_schema()
def order_documents(context, params, execution):
    """Documentos que pide la empresa (y Hurgo) para el pedido, con lo ya subido."""
    data = validate_input(Sz_order_doc_in, context)
    return results(S_document().order_documents(context_user(context), data["order_id"]))


@register_module("orders.attach", important=True)
@in_company_schema()
def attach_order(context, params, execution):
    """Sube documentos al pedido (multipart: order_id, document_key, files)."""
    user = context_user(context)
    files = validate_files(context_files(context), validate_attach)
    data = validate_input(Sz_order_doc_in, context)
    S_document().attach_order(user, data["order_id"], data.get("document_key"), files)
    return results(S_document().order_documents(user, data["order_id"]))


@register_module("trips.documents", important=True)
@in_company_schema(company_from=trip_company)
def trip_documents(context, params, execution):
    """Documentos de cargue del viaje y de entrega por parada, con lo ya subido."""
    data = validate_input(Sz_trip_doc_in, context)
    return results(S_document().trip_documents(context_user(context), data["trip_id"]))


@register_module("trips.attach", important=True)
@in_company_schema(company_from=trip_company)
def attach_trip(context, params, execution):
    """Sube documentos de cargue o de entrega (multipart: trip_id, document_key, trip_line_id?, files)."""
    user = context_user(context)
    files = validate_files(context_files(context), validate_attach)
    data = validate_input(Sz_trip_doc_in, context)
    S_document().attach_trip(user, data["trip_id"], data.get("document_key"), files, data.get("trip_line_id"))
    return results(S_document().trip_documents(user, data["trip_id"]))
