from decimal import Decimal

from django.core.validators import FileExtensionValidator
from rest_framework import serializers

from enginedj.base.serializers.sz_common import Sz_position_in, person
from apps.orders.models import M_trip_line_serie
from apps.trips.models import M_trip, M_trip_attach, M_trip_event, M_trip_line

ATTACH_EXTENSIONS = ["jpg", "jpeg", "png", "webp", "heic", "heif", "pdf"]
MAX_ATTACH_MB = 10


def validate_attach(file):
    """Fotos o PDF de hasta 10 MB (remisión firmada, novedades, devoluciones)."""
    FileExtensionValidator(ATTACH_EXTENSIONS)(file)
    if file.size > MAX_ATTACH_MB * 1024 * 1024:
        raise serializers.ValidationError(f"El archivo supera {MAX_ATTACH_MB} MB.")


# ----------------------------------------------------------------------
# Salida
# ----------------------------------------------------------------------
class Sz_trip_attach(serializers.ModelSerializer):
    type = serializers.CharField(source="type_attach_id.name", read_only=True)
    type_key = serializers.CharField(source="type_attach_id.key", read_only=True)
    trip_line_id = serializers.IntegerField(source="trip_line_id_id", read_only=True)

    class Meta:
        model = M_trip_attach
        fields = ["id", "trip_line_id", "type", "type_key", "file", "description", "latitude", "longitude",
                  "create_date"]


class Sz_trip_event(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    trip_line_id = serializers.IntegerField(source="trip_line_id_id", read_only=True)
    event_type_display = serializers.CharField(source="get_event_type_display", read_only=True)

    class Meta:
        model = M_trip_event
        fields = ["id", "trip_line_id", "event_type", "event_type_display", "name", "description", "from_state",
                  "to_state", "event_date", "latitude", "longitude", "user"]

    def get_user(self, obj):
        return person(obj.user_id)


class Sz_trip_line_serie(serializers.ModelSerializer):
    order_line_trip_id = serializers.IntegerField(source="order_line_trip_id_id", read_only=True)

    class Meta:
        model = M_trip_line_serie
        fields = ["id", "order_line_trip_id", "vin", "engine_number", "state"]


class Sz_trip_line(serializers.ModelSerializer):
    state_display = serializers.CharField(source="get_state_display", read_only=True)
    recipient = serializers.SerializerMethodField()
    address = serializers.SerializerMethodField()
    items = serializers.SerializerMethodField()
    series = Sz_trip_line_serie(source="trip_line_serie_trip_line_id", many=True, read_only=True)

    class Meta:
        model = M_trip_line
        fields = ["id", "sequence", "state", "state_display", "recipient", "address", "estimated_date",
                  "delivery_date", "qty", "weight_kg", "is_return", "return_reason", "rating", "comment",
                  "items", "series"]

    def get_recipient(self, obj):
        return {"id": obj.recipient_id_id, "name": obj.recipient_id.name}

    def get_address(self, obj):
        """Copia de la dirección guardada en la parada (la dirección vive en el esquema de la empresa)."""
        return {"id": obj.address_ref, "name": obj.address_name, "address": obj.address_text,
                "location": obj.location_name, "description": obj.address_description,
                "contact_name": obj.contact_name, "contact_phone": obj.contact_phone,
                "latitude": obj.latitude, "longitude": obj.longitude}

    def get_items(self, obj):
        return [
            {
                "order_line_trip_id": a.id,
                "order_code": a.order_line_id.order_id.code,
                "order_line_id": a.order_line_id_id,
                "item_id": a.order_line_id.item_id_id,
                "item": a.order_line_id.item_id.name,
                "is_serialized": a.order_line_id.item_id.is_serialized,
                "qty": a.qty,
            }
            for a in obj.order_line_trip_trip_line_id.all()
        ]


class Sz_trip_list(serializers.ModelSerializer):
    state_display = serializers.CharField(source="get_state_display", read_only=True)
    trip_type_display = serializers.CharField(source="get_trip_type_display", read_only=True)
    company = serializers.SerializerMethodField()
    brand = serializers.CharField(source="brand_name", read_only=True)
    vehicle = serializers.CharField(source="vehicle_id.plate", default=None, read_only=True)
    driver = serializers.SerializerMethodField()
    origin_address = serializers.CharField(source="origin_address_id.name", default=None, read_only=True)
    parent_trip = serializers.CharField(source="parent_trip_id.code", default=None, read_only=True)

    class Meta:
        model = M_trip
        fields = ["id", "code", "trip_type", "trip_type_display", "state", "state_display", "company", "brand",
                  "vehicle", "driver", "origin_address", "parent_trip", "planned_departure", "departure_date",
                  "closed_date", "create_date"]

    def get_company(self, obj):
        return {"id": obj.company_id_id, "name": obj.company_id.name}

    def get_driver(self, obj):
        return person(obj.driver_id.user_id) if obj.driver_id_id else None


class Sz_trip_driver(Sz_trip_list):
    """Viaje en la lista de la app del conductor (``trips.mine``): resumen de paradas para la tarjeta.

    Espera las paradas precargadas (``R_trip.active_for_driver_user``).
    """

    origin_location = serializers.CharField(source="origin_address_id.location_id.name", default=None, read_only=True)
    destination = serializers.SerializerMethodField()
    stops_total = serializers.SerializerMethodField()
    stops_done = serializers.SerializerMethodField()
    total_qty = serializers.SerializerMethodField()

    class Meta(Sz_trip_list.Meta):
        fields = Sz_trip_list.Meta.fields + ["origin_location", "destination", "stops_total", "stops_done",
                                             "total_qty"]

    @staticmethod
    def _stops(obj):
        return sorted((line for line in obj.trip_line_trip_id.all() if line.is_active), key=lambda l: l.sequence)

    def get_destination(self, obj):
        stops = self._stops(obj)
        if not stops:
            return None
        last = stops[-1]
        return {"recipient": last.recipient_id.name, "name": last.address_name, "location": last.location_name}

    def get_stops_total(self, obj):
        return len(self._stops(obj))

    def get_stops_done(self, obj):
        return sum(1 for line in self._stops(obj) if line.state in ("delivered", "returned"))

    def get_total_qty(self, obj):
        return str(sum((line.qty for line in self._stops(obj)), Decimal("0")))


class Sz_trip_detail(Sz_trip_list):
    lines = Sz_trip_line(source="trip_line_trip_id", many=True, read_only=True)
    events = Sz_trip_event(source="trip_event_trip_id", many=True, read_only=True)
    attachments = Sz_trip_attach(source="trip_attach_trip_id", many=True, read_only=True)

    class Meta(Sz_trip_list.Meta):
        fields = Sz_trip_list.Meta.fields + ["notes", "lines", "events", "attachments"]


# ----------------------------------------------------------------------
# Entrada
# ----------------------------------------------------------------------
class Sz_trip_id_in(serializers.Serializer):
    trip_id = serializers.IntegerField()


class Sz_trip_line_in(Sz_trip_id_in):
    trip_line_id = serializers.IntegerField()


class Sz_allocation_in(serializers.Serializer):
    order_line_id = serializers.IntegerField()
    qty = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))


class Sz_trip_build_in(serializers.Serializer):
    company_id = serializers.IntegerField()
    origin_address_id = serializers.IntegerField(required=False, allow_null=True,
                                                 help_text="Lugar de cargue; vacío = el de los pedidos.")
    planned_departure = serializers.DateTimeField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    allocations = Sz_allocation_in(many=True, allow_empty=False)


class Sz_allocations_in(Sz_trip_id_in):
    allocations = Sz_allocation_in(many=True, allow_empty=False)


class Sz_serie_in(serializers.Serializer):
    order_line_trip_id = serializers.IntegerField()
    vin = serializers.CharField(max_length=30)
    engine_number = serializers.CharField(max_length=30, required=False, allow_blank=True, default="")


class Sz_series_in(Sz_trip_line_in):
    series = Sz_serie_in(many=True, allow_empty=False)


class Sz_assign_in(Sz_trip_id_in):
    vehicle_id = serializers.IntegerField()
    driver_id = serializers.IntegerField()
    carrier_id = serializers.IntegerField(required=False, allow_null=True)


class Sz_cancel_in(Sz_trip_id_in):
    reason = serializers.CharField()


class Sz_depart_in(Sz_trip_id_in, Sz_position_in):
    pass


class Sz_stop_position_in(Sz_trip_line_in, Sz_position_in):
    pass


class Sz_deliver_in(Sz_trip_line_in, Sz_position_in):
    rating = serializers.IntegerField(required=False, allow_null=True, min_value=1, max_value=5)
    comment = serializers.CharField(required=False, allow_blank=True, default="")


class Sz_return_in(Sz_trip_line_in, Sz_position_in):
    reason = serializers.CharField()


class Sz_novelty_in(Sz_trip_id_in, Sz_position_in):
    name = serializers.CharField(max_length=150)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    trip_line_id = serializers.IntegerField(required=False, allow_null=True)


class Sz_return_trip_in(Sz_trip_line_in):
    origin_address_id = serializers.IntegerField(required=False, allow_null=True)


class Sz_pending_lines_in(serializers.Serializer):
    company_id = serializers.IntegerField(required=False, allow_null=True)
