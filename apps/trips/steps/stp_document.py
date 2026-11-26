"""Documentos del pedido y del viaje (subir y consultar los requeridos por etapa)."""

from rest_framework import serializers

from enginedj.base.steps.helpers import context_files, context_user, results, validate_files, validate_input
from enginedj.modules.registry import register_module

from apps.trips.serializers import validate_attach
from apps.trips.services import S_document


class Sz_order_doc_in(serializers.Serializer):
    order_id = serializers.IntegerField()
    type_attach_id = serializers.IntegerField(required=False)


class Sz_trip_doc_in(serializers.Serializer):
    trip_id = serializers.IntegerField()
    type_attach_id = serializers.IntegerField(required=False)
    trip_line_id = serializers.IntegerField(required=False, allow_null=True)


@register_module("orders.documents", important=True)
def order_documents(context, params, execution):
    """Documentos que pide la empresa (y Hurgo) para el pedido, con lo ya subido."""
    data = validate_input(Sz_order_doc_in, context)
    return results(S_document().order_documents(context_user(context), data["order_id"]))


@register_module("orders.attach", important=True)
def attach_order(context, params, execution):
    """Sube documentos al pedido (multipart: order_id, type_attach_id, files)."""
    user = context_user(context)
    files = validate_files(context_files(context), validate_attach)
    data = validate_input(Sz_order_doc_in, context)
    S_document().attach_order(user, data["order_id"], data.get("type_attach_id"), files)
    return results(S_document().order_documents(user, data["order_id"]))


@register_module("trips.documents", important=True)
def trip_documents(context, params, execution):
    """Documentos de cargue del viaje y de entrega por parada, con lo ya subido."""
    data = validate_input(Sz_trip_doc_in, context)
    return results(S_document().trip_documents(context_user(context), data["trip_id"]))


@register_module("trips.attach", important=True)
def attach_trip(context, params, execution):
    """Sube documentos de cargue o de entrega (multipart: trip_id, type_attach_id, trip_line_id?, files)."""
    user = context_user(context)
    files = validate_files(context_files(context), validate_attach)
    data = validate_input(Sz_trip_doc_in, context)
    S_document().attach_trip(user, data["trip_id"], data.get("type_attach_id"), files, data.get("trip_line_id"))
    return results(S_document().trip_documents(user, data["trip_id"]))
