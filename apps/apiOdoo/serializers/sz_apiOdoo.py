from rest_framework import serializers

from apps.apiOdoo.models import M_odoo_purchase


class Sz_odoo_purchase(serializers.ModelSerializer):
    class Meta:
        model = M_odoo_purchase
        fields = ["id", "odoo_id", "name", "partner_odoo_id", "partner_name", "state", "date_order", "amount_total",
                  "synced_date"]


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
