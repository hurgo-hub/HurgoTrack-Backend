from decimal import Decimal

from rest_framework import serializers

from enginedj.base.serializers.sz_common import person
from apps.orders.models import M_item, M_order, M_order_event, M_order_line


def _address(address):
    if address is None:
        return None
    return {"id": address.id, "name": address.name, "address": address.address, "location": address.location_id.name}


# ----------------------------------------------------------------------
# Salida
# ----------------------------------------------------------------------
class Sz_order_event(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()

    class Meta:
        model = M_order_event
        fields = ["id", "name", "description", "from_state", "to_state", "event_date", "user"]

    def get_user(self, obj):
        return person(obj.user_id)


class Sz_order_line(serializers.ModelSerializer):
    item = serializers.SerializerMethodField()
    recipient = serializers.SerializerMethodField()
    address = serializers.SerializerMethodField()
    state_display = serializers.CharField(source="get_state_display", read_only=True)
    qty_pending = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    trips = serializers.SerializerMethodField()

    class Meta:
        model = M_order_line
        fields = ["id", "item", "recipient", "address", "qty", "qty_assigned", "qty_delivered", "qty_pending",
                  "state", "state_display", "trips"]

    def get_item(self, obj):
        item = obj.item_id
        return {"id": item.id, "name": item.name, "sku": item.sku, "unit": item.unit,
                "brand": item.brand_id.name if item.brand_id_id else None, "is_serialized": item.is_serialized}

    def get_recipient(self, obj):
        return {"id": obj.recipient_id_id, "name": obj.recipient_id.name}

    def get_address(self, obj):
        return _address(obj.address_id)

    def get_trips(self, obj):
        """Seguimiento: en qué viajes va la línea y cómo va cada entrega."""
        return [
            {
                "trip_id": a.trip_line_id.trip_id_id,
                "trip_code": a.trip_line_id.trip_id.code,
                "trip_state": a.trip_line_id.trip_id.state,
                "trip_type": a.trip_line_id.trip_id.trip_type,
                "stop_state": a.trip_line_id.state,
                "qty": a.qty,
                "delivery_date": a.trip_line_id.delivery_date,
            }
            for a in obj.order_line_trip_order_line_id.all()
        ]


class Sz_order_detail(serializers.ModelSerializer):
    state_display = serializers.CharField(source="get_state_display", read_only=True)
    company = serializers.SerializerMethodField()
    address = serializers.SerializerMethodField()
    created_by = serializers.SerializerMethodField()
    lines = Sz_order_line(source="order_line_order_id", many=True, read_only=True)
    events = Sz_order_event(source="order_event_order_id", many=True, read_only=True)

    class Meta:
        model = M_order
        fields = ["id", "code", "order_date", "state", "state_display", "company", "address", "odoo_purchase",
                  "confirmed_date", "created_by", "create_date", "notes", "lines", "events"]

    def get_company(self, obj):
        return {"id": obj.company_id_id, "name": obj.company_id.name}

    def get_address(self, obj):
        return _address(obj.address_id)

    def get_created_by(self, obj):
        return person(obj.create_user)


class Sz_item_lookup(serializers.ModelSerializer):
    type_item = serializers.CharField(source="type_item_id.name", read_only=True)
    unit = serializers.CharField(read_only=True)
    brand = serializers.CharField(source="brand_id.name", default=None, read_only=True)

    class Meta:
        model = M_item
        fields = ["id", "company_id", "sku", "name", "type_item", "brand", "unit", "weight_kg", "is_vehicle",
                  "is_serialized"]


class Sz_pending_order_line(serializers.ModelSerializer):
    order_code = serializers.CharField(source="order_id.code", read_only=True)
    company_id = serializers.IntegerField(source="order_id.company_id_id", read_only=True)
    company = serializers.CharField(source="order_id.company_id.name", read_only=True)
    recipient = serializers.CharField(source="recipient_id.name", read_only=True)
    address = serializers.CharField(source="address_id.name", read_only=True)
    item = serializers.CharField(source="item_id.name", read_only=True)
    brand = serializers.CharField(source="item_id.brand_id.name", default=None, read_only=True)
    qty_pending = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    loading_address_id = serializers.IntegerField(source="order_id.address_id_id", read_only=True, allow_null=True)
    loading_address = serializers.CharField(source="order_id.address_id.name", default=None, read_only=True)
    uses_stock = serializers.BooleanField(source="item_id.type_item_id.uses_stock", read_only=True)
    stock_available = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True, allow_null=True,
                                               default=None)

    class Meta:
        model = M_order_line
        fields = ["id", "order_id", "order_code", "company_id", "company", "recipient", "address", "item_id", "item", "brand",
                  "qty", "qty_assigned", "qty_delivered", "qty_pending", "state", "loading_address_id",
                  "loading_address", "uses_stock", "stock_available"]


# ----------------------------------------------------------------------
# Entrada
# ----------------------------------------------------------------------
class Sz_order_line_in(serializers.Serializer):
    item_id = serializers.IntegerField()
    qty = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    address_id = serializers.IntegerField(help_text="Dirección de entrega de la empresa que pide.")


class Sz_order_in(serializers.Serializer):
    company_id = serializers.IntegerField(required=False, allow_null=True)
    address_id = serializers.IntegerField(required=False, allow_null=True,
                                          help_text="Lugar de cargue (opcional: lo puede elegir Hurgo después).")
    order_date = serializers.DateField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    lines = Sz_order_line_in(many=True, allow_empty=False)
    submit = serializers.BooleanField(required=False, default=True)


class Sz_order_update_in(Sz_order_in):
    order_id = serializers.IntegerField()


class Sz_order_id_in(serializers.Serializer):
    order_id = serializers.IntegerField()


class Sz_confirm_in(Sz_order_id_in):
    odoo_purchase = serializers.CharField(max_length=60, required=False, allow_blank=True, default="",
                                          help_text="Obligatoria salvo pedidos de productos con stock (materiales).")
    loading_address_id = serializers.IntegerField(required=False, allow_null=True)


class Sz_loading_point_in(Sz_order_id_in):
    address_id = serializers.IntegerField(help_text="Lugar de cargue registrado (locations.loading_points).")


class Sz_cancel_in(Sz_order_id_in):
    reason = serializers.CharField()


class Sz_lookup_in(serializers.Serializer):
    company_id = serializers.IntegerField(required=False, allow_null=True)
    q = serializers.CharField(required=False, allow_blank=True, default="")


class Sz_item(serializers.ModelSerializer):
    type_item = serializers.CharField(source="type_item_id.name", read_only=True)
    unit = serializers.CharField(read_only=True)
    unit_name = serializers.CharField(source="unit_id.name", default=None, read_only=True)
    brand = serializers.CharField(source="brand_id.name", default=None, read_only=True)
    uses_stock = serializers.BooleanField(source="type_item_id.uses_stock", read_only=True)
    loading_tags = serializers.SerializerMethodField()

    class Meta:
        model = M_item
        fields = ["id", "company_id", "type_item_id", "type_item", "uses_stock", "sku", "odoo_ref", "name",
                  "description", "unit_id", "unit", "unit_name", "brand_id", "brand", "weight_kg", "is_serialized",
                  "is_active", "loading_tags"]

    def get_loading_tags(self, obj):
        return [{"id": t.id, "name": t.name} for t in obj.loading_tags.all()]


class Sz_item_in(serializers.Serializer):
    item_id = serializers.IntegerField(required=False, allow_null=True, help_text="Vacío = crear.")
    company_id = serializers.IntegerField()
    type_item_id = serializers.IntegerField()
    name = serializers.CharField(max_length=200)
    unit_id = serializers.IntegerField(required=False, allow_null=True, help_text="Unidad de la empresa o común.")
    unit = serializers.CharField(max_length=20, required=False, help_text="Código de la unidad (alternativa a unit_id).")
    brand_id = serializers.IntegerField(required=False, allow_null=True)
    weight_kg = serializers.DecimalField(max_digits=10, decimal_places=3, required=False, allow_null=True)
    sku = serializers.CharField(max_length=60, required=False, allow_blank=True)
    odoo_ref = serializers.CharField(max_length=60, required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    loading_tag_ids = serializers.ListField(child=serializers.IntegerField(), required=False)
    is_active = serializers.BooleanField(required=False)


class Sz_company_items_in(serializers.Serializer):
    company_id = serializers.IntegerField()
