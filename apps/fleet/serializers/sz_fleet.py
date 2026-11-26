"""Entrada y salida de la gestión de flota (vehículos, propietarios, SOAT, revisión técnico-mecánica)."""

from django.utils import timezone
from rest_framework import serializers

from enginedj.base.choices import DOCUMENT_TYPE_CHOICES, LICENSE_CATEGORY_CHOICES

from apps.companies.uploads import display_name
from apps.fleet.models import M_mechanical_inspection, M_partner, M_soat, M_vehicle


class OptionalInt(serializers.IntegerField):
    """Entero opcional: vacío ("") = quitar el valor."""

    def to_internal_value(self, data):
        return None if data in ("", None) else super().to_internal_value(data)


class OptionalDecimal(serializers.DecimalField):
    def to_internal_value(self, data):
        return None if data in ("", None) else super().to_internal_value(data)


def _blank(choices):
    return serializers.ChoiceField(choices=choices, required=False, allow_blank=True)


# ----------------------------------------------------------------------
# Entrada
# ----------------------------------------------------------------------
class Sz_vehicle_in(serializers.Serializer):
    vehicle_id = serializers.IntegerField(required=False, allow_null=True, help_text="Vacío = crear.")
    plate = serializers.CharField(max_length=10, required=False)
    type_vehicle_id = serializers.IntegerField(required=False)
    brand_vehicle_id = serializers.IntegerField(required=False)
    owner_id = serializers.IntegerField(required=False)
    holder_id = OptionalInt(required=False, allow_null=True)
    bodywork_id = OptionalInt(required=False, allow_null=True)
    transit_id = OptionalInt(required=False, allow_null=True)
    model_year = OptionalInt(required=False, allow_null=True, min_value=1950, max_value=2100)
    color = serializers.CharField(max_length=60, required=False, allow_blank=True)
    load_capacity_kg = OptionalDecimal(max_digits=10, decimal_places=2, required=False, allow_null=True, min_value=0)
    empty_weight_kg = OptionalDecimal(max_digits=10, decimal_places=2, required=False, allow_null=True, min_value=0)
    motorcycle_capacity = OptionalInt(required=False, allow_null=True, min_value=0)
    vin = serializers.CharField(max_length=30, required=False, allow_blank=True)
    fuel_type = _blank(M_vehicle.fuel_type_choices)
    license_category = _blank(LICENSE_CATEGORY_CHOICES)
    transmission = _blank(M_vehicle.transmission_choices)
    is_available = serializers.BooleanField(required=False)
    is_active = serializers.BooleanField(required=False)


class Sz_partner_in(serializers.Serializer):
    partner_id = serializers.IntegerField(required=False, allow_null=True, help_text="Vacío = crear.")
    name = serializers.CharField(max_length=200, required=False)
    is_company = serializers.BooleanField(required=False)
    document_type = serializers.ChoiceField(choices=DOCUMENT_TYPE_CHOICES, required=False)
    document_number = serializers.CharField(max_length=20, required=False)
    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(max_length=40, required=False, allow_blank=True)
    address = serializers.CharField(max_length=255, required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False)


class Sz_soat_in(serializers.Serializer):
    vehicle_id = serializers.IntegerField()
    insurer_name = serializers.CharField(max_length=150)
    policy_number = serializers.CharField(max_length=60)
    date_start = serializers.DateField(required=False, allow_null=True)
    date_expire = serializers.DateField()

    def validate(self, attrs):
        if attrs.get("date_start") and attrs["date_start"] > attrs["date_expire"]:
            raise serializers.ValidationError("La fecha de inicio es posterior al vencimiento.")
        return attrs


class Sz_rtm_in(serializers.Serializer):
    vehicle_id = serializers.IntegerField()
    certificate_number = serializers.CharField(max_length=60)
    cda_name = serializers.CharField(max_length=150)
    date_expedition = serializers.DateField()
    date_expire = serializers.DateField()

    def validate(self, attrs):
        if attrs["date_expedition"] > attrs["date_expire"]:
            raise serializers.ValidationError("La fecha de expedición es posterior al vencimiento.")
        return attrs


# ----------------------------------------------------------------------
# Salida
# ----------------------------------------------------------------------
class _Expiring(serializers.ModelSerializer):
    valid = serializers.SerializerMethodField()
    file_name = serializers.SerializerMethodField()

    def get_valid(self, obj):
        return obj.date_expire >= timezone.localdate()

    def get_file_name(self, obj):
        return display_name(obj.file) if obj.file else None


class Sz_soat(_Expiring):
    class Meta:
        model = M_soat
        fields = ["id", "insurer_name", "policy_number", "date_start", "date_expire", "valid", "file_name"]


class Sz_rtm(_Expiring):
    class Meta:
        model = M_mechanical_inspection
        fields = ["id", "certificate_number", "cda_name", "date_expedition", "date_expire", "valid", "file_name"]


class Sz_partner(serializers.ModelSerializer):
    class Meta:
        model = M_partner
        fields = ["id", "name", "is_company", "document_type", "document_number", "email", "phone", "address",
                  "is_active"]


def _latest(rows):
    rows = [r for r in rows if r.is_active]
    return max(rows, key=lambda r: r.date_expire) if rows else None


class Sz_vehicle(serializers.ModelSerializer):
    type_vehicle = serializers.CharField(source="type_vehicle_id.name", read_only=True)
    brand_vehicle = serializers.CharField(source="brand_vehicle_id.name", read_only=True)
    owner = serializers.CharField(source="owner_id.name", read_only=True)
    soat = serializers.SerializerMethodField()
    rtm = serializers.SerializerMethodField()
    rtm_required = serializers.SerializerMethodField()

    class Meta:
        model = M_vehicle
        fields = ["id", "plate", "type_vehicle_id", "type_vehicle", "brand_vehicle_id", "brand_vehicle", "owner_id",
                  "owner", "holder_id", "bodywork_id", "transit_id", "model_year", "color", "load_capacity_kg",
                  "empty_weight_kg", "motorcycle_capacity", "vin", "fuel_type", "license_category", "transmission",
                  "is_available", "is_active", "soat", "rtm", "rtm_required"]

    def get_soat(self, obj):
        soat = _latest(obj.soat_vehicle_id.all())
        return Sz_soat(soat).data if soat else None

    def get_rtm(self, obj):
        rtm = _latest(obj.mechanical_inspection_vehicle_id.all())
        return Sz_rtm(rtm).data if rtm else None

    def get_rtm_required(self, obj):
        """Los vehículos nuevos (modelo del año o del anterior) aún no necesitan revisión técnico-mecánica."""
        return not (obj.model_year is not None and timezone.localdate().year - obj.model_year <= 1)
