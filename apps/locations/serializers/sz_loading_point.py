from rest_framework import serializers

from apps.locations.models import M_address, M_loading_tag


class Sz_loading_tag(serializers.ModelSerializer):
    class Meta:
        model = M_loading_tag
        fields = ["id", "name"]


class Sz_loading_point(serializers.ModelSerializer):
    company = serializers.SerializerMethodField()
    location = serializers.CharField(source="location_id.name", read_only=True)
    tags = Sz_loading_tag(many=True, read_only=True)
    suggested = serializers.SerializerMethodField()
    matching_tags = serializers.SerializerMethodField()

    class Meta:
        model = M_address
        fields = ["id", "name", "address", "description", "location_id", "location", "company", "contact_name",
                  "contact_phone", "latitude", "longitude", "is_active", "tags", "suggested", "matching_tags"]

    def get_company(self, obj):
        return {"id": obj.company_id_id, "name": obj.company_id.name}

    def get_suggested(self, obj):
        return getattr(obj, "suggested", False)

    def get_matching_tags(self, obj):
        return getattr(obj, "matching_tags", [])


# ----------------------------------------------------------------------
# Entrada
# ----------------------------------------------------------------------
class Sz_loading_points_in(serializers.Serializer):
    company_id = serializers.IntegerField(required=False, allow_null=True)
    tag_ids = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)
    item_ids = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)
    order_id = serializers.IntegerField(required=False, allow_null=True,
                                        help_text="Sugiere los lugares con etiquetas de los productos del pedido.")
    q = serializers.CharField(required=False, allow_blank=True, default="")


class Sz_loading_point_in(serializers.Serializer):
    address_id = serializers.IntegerField(required=False, allow_null=True, help_text="Vacío = crear.")
    company_id = serializers.IntegerField(help_text="Empresa dueña del sitio (cliente o proveedor).")
    location_id = serializers.IntegerField(help_text="Municipio.")
    name = serializers.CharField(max_length=120)
    address = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    contact_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    contact_phone = serializers.CharField(required=False, allow_blank=True, max_length=40)
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    tag_ids = serializers.ListField(child=serializers.IntegerField(), required=False)
    is_active = serializers.BooleanField(required=False)


class Sz_tag_in(serializers.Serializer):
    name = serializers.CharField(max_length=120)


class Sz_tags_in(serializers.Serializer):
    q = serializers.CharField(required=False, allow_blank=True, default="")
