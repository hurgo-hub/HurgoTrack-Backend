from decimal import Decimal

from rest_framework import serializers

from enginedj.base.serializers.sz_common import person
from apps.stock.models import M_purchase_request, M_purchase_request_line, M_stock, M_stock_move


# ----------------------------------------------------------------------
# Salida
# ----------------------------------------------------------------------
class Sz_stock(serializers.ModelSerializer):
    company = serializers.CharField(source="company_id.name", read_only=True)
    item = serializers.CharField(source="item_id.name", read_only=True)
    unit = serializers.CharField(source="item_id.unit", read_only=True)

    class Meta:
        model = M_stock
        fields = ["id", "company_id", "company", "item_id", "item", "unit", "qty_available", "update_date"]


class Sz_stock_move(serializers.ModelSerializer):
    item = serializers.CharField(source="item_id.name", read_only=True)
    move_type_display = serializers.CharField(source="get_move_type_display", read_only=True)
    user = serializers.SerializerMethodField()
    odoo_purchase = serializers.CharField(source="odoo_purchase_line_id.purchase_id.name", default=None, read_only=True)
    purchase_request = serializers.CharField(source="purchase_request_id.code", default=None, read_only=True)
    trip_code = serializers.CharField(source="order_line_trip_id.trip_line_id.trip_id.code", default=None,
                                      read_only=True)
    order_code = serializers.CharField(source="order_line_trip_id.order_line_id.order_id.code", default=None,
                                       read_only=True)

    class Meta:
        model = M_stock_move
        fields = ["id", "move_date", "company_id", "item_id", "item", "move_type", "move_type_display", "qty",
                  "balance", "odoo_purchase", "purchase_request", "trip_code", "order_code", "description", "user"]

    def get_user(self, obj):
        return person(obj.create_user) if obj.create_user_id else None


class Sz_requirement(serializers.Serializer):
    item_id = serializers.IntegerField()
    item = serializers.CharField()
    unit = serializers.CharField()
    pending = serializers.DecimalField(max_digits=14, decimal_places=2)
    available = serializers.DecimalField(max_digits=14, decimal_places=2)
    in_requests = serializers.DecimalField(max_digits=14, decimal_places=2)
    to_buy = serializers.DecimalField(max_digits=14, decimal_places=2)


class Sz_purchase_request_line(serializers.ModelSerializer):
    item = serializers.CharField(source="item_id.name", read_only=True)
    order_code = serializers.CharField(source="order_line_id.order_id.code", default=None, read_only=True)

    class Meta:
        model = M_purchase_request_line
        fields = ["id", "item_id", "item", "qty", "order_line_id", "order_code"]


class Sz_purchase_request(serializers.ModelSerializer):
    state_display = serializers.CharField(source="get_state_display", read_only=True)
    company = serializers.SerializerMethodField()
    created_by = serializers.SerializerMethodField()
    lines = Sz_purchase_request_line(source="purchase_request_line_purchase_request_id", many=True, read_only=True)
    odoo_purchases = serializers.SerializerMethodField()

    class Meta:
        model = M_purchase_request
        fields = ["id", "code", "state", "state_display", "company", "notes", "sent_date", "purchased_date",
                  "create_date", "created_by", "lines", "odoo_purchases"]

    def get_company(self, obj):
        return {"id": obj.company_id_id, "name": obj.company_id.name}

    def get_created_by(self, obj):
        return person(obj.create_user) if obj.create_user_id else None

    def get_odoo_purchases(self, obj):
        return [{"id": p.id, "name": p.name, "state": p.state} for p in obj.odoo_purchases.all()]


# ----------------------------------------------------------------------
# Entrada
# ----------------------------------------------------------------------
class Sz_company_in(serializers.Serializer):
    company_id = serializers.IntegerField()


class Sz_stock_list_in(serializers.Serializer):
    company_id = serializers.IntegerField(required=False, allow_null=True)
    only_available = serializers.BooleanField(required=False, default=False)


class Sz_moves_in(serializers.Serializer):
    company_id = serializers.IntegerField(required=False, allow_null=True)
    item_id = serializers.IntegerField(required=False, allow_null=True)


class Sz_adjust_in(serializers.Serializer):
    company_id = serializers.IntegerField()
    item_id = serializers.IntegerField()
    qty = serializers.DecimalField(max_digits=14, decimal_places=2, help_text="Positivo entra, negativo sale.")
    reason = serializers.CharField(max_length=255)


class Sz_request_line_in(serializers.Serializer):
    item_id = serializers.IntegerField()
    qty = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"))
    order_line_id = serializers.IntegerField(required=False, allow_null=True)


class Sz_request_in(serializers.Serializer):
    company_id = serializers.IntegerField()
    lines = Sz_request_line_in(many=True, allow_empty=False)
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    send = serializers.BooleanField(required=False, default=True, help_text="false = dejar en borrador.")


class Sz_request_id_in(serializers.Serializer):
    purchase_request_id = serializers.IntegerField()


class Sz_request_cancel_in(Sz_request_id_in):
    reason = serializers.CharField()


class Sz_link_purchase_in(Sz_request_id_in):
    odoo_purchase = serializers.CharField(max_length=60, help_text="Referencia de la compra en Odoo, ej. P00012.")


class Sz_request_list_in(serializers.Serializer):
    company_id = serializers.IntegerField(required=False, allow_null=True)
    state = serializers.ChoiceField(choices=[c[0] for c in M_purchase_request.state_choices], required=False,
                                    allow_null=True)
