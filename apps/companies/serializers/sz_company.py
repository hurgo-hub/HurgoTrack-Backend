from rest_framework import serializers

from apps.companies.models import M_company


class Sz_recipient_lookup(serializers.ModelSerializer):
    addresses = serializers.SerializerMethodField()

    class Meta:
        model = M_company
        fields = ["id", "name", "document_number", "addresses"]

    def get_addresses(self, obj):
        return [
            {"id": a.id, "name": a.name, "address": a.address, "location": a.location_id.name}
            for a in getattr(obj, "active_addresses", [])
        ]
