from enginedj.modules.registry import register_module

from enginedj.base.steps.helpers import results
from apps.fleet.services import S_vehicle


@register_module("fleet.document_expirations", important=True)
def document_expirations(context, params, execution):
    """SOAT, revisión técnico-mecánica y licencias vencidas o por vencer."""
    days = context.get("days")
    return results(S_vehicle().document_expirations(int(days) if days not in (None, "") else None))


# ----------------------------------------------------------------------
# Documentos de flota (vehículo / conductor)
# ----------------------------------------------------------------------
from rest_framework import serializers  # noqa: E402

from enginedj.base.steps.helpers import context_files, context_user, validate_files, validate_input  # noqa: E402

from apps.fleet.services import S_fleet_document  # noqa: E402
from apps.trips.serializers import validate_attach  # noqa: E402


class Sz_fleet_owner_in(serializers.Serializer):
    vehicle_id = serializers.IntegerField(required=False, allow_null=True)
    driver_id = serializers.IntegerField(required=False, allow_null=True)

    def validate(self, attrs):
        if bool(attrs.get("vehicle_id")) == bool(attrs.get("driver_id")):
            raise serializers.ValidationError("Indica vehicle_id o driver_id.")
        return attrs


class Sz_fleet_upload_in(Sz_fleet_owner_in):
    type_id = serializers.IntegerField()
    date_expire = serializers.DateField(required=False, allow_null=True)


@register_module("fleet.documents", important=True)
def fleet_documents(context, params, execution):
    """Documentos que exige Hurgo a un vehículo o conductor, con lo subido y si está vigente."""
    data = validate_input(Sz_fleet_owner_in, context)
    return results(S_fleet_document().documents(context_user(context), vehicle_id=data.get("vehicle_id"),
                                                driver_id=data.get("driver_id")))


@register_module("fleet.document.upload", important=True)
def upload_fleet_document(context, params, execution):
    """Sube un documento de flota (multipart: vehicle_id o driver_id, type_id, date_expire, files)."""
    user = context_user(context)
    files = validate_files(context_files(context), validate_attach)
    data = validate_input(Sz_fleet_upload_in, context)
    return results(S_fleet_document().upload(user, type_id=data["type_id"], files=files,
                                             date_expire=data.get("date_expire"), vehicle_id=data.get("vehicle_id"),
                                             driver_id=data.get("driver_id")))
