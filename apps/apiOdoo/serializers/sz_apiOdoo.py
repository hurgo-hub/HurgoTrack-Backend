from rest_framework import serializers

from apps.apiOdoo.models import M_odoo_purchase, M_odoo_purchase_line


class Sz_odoo_purchase_line(serializers.ModelSerializer):
    item = serializers.CharField(source="item_id.name", default=None, read_only=True)

    class Meta:
        model = M_odoo_purchase_line
        fields = ["id", "odoo_line_id", "product_odoo_id", "product_name", "item_id", "item", "product_qty",
                  "qty_received", "uom_name", "qty_stocked"]


class Sz_odoo_purchase(serializers.ModelSerializer):
    lines = Sz_odoo_purchase_line(source="odoo_purchase_line_purchase_id", many=True, read_only=True)

    class Meta:
        model = M_odoo_purchase
        fields = ["id", "odoo_id", "name", "partner_odoo_id", "partner_name", "state", "date_order", "amount_total",
                  "synced_date", "lines"]


class Sz_purchase_in(serializers.Serializer):
    name = serializers.CharField(max_length=60)


class Sz_sync_partners_in(serializers.Serializer):
    domain = serializers.JSONField(required=False)
    limit = serializers.IntegerField(required=False, min_value=1)


class Sz_sync_products_in(Sz_sync_partners_in):
    company_id = serializers.IntegerField()
    type_item_id = serializers.IntegerField()


class Sz_order_id_in(serializers.Serializer):
    order_id = serializers.IntegerField()
