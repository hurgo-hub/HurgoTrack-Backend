"""Entrada y salida de la gestión de conductores."""

from django.utils import timezone
from rest_framework import serializers

from enginedj.base.choices import DOCUMENT_TYPE_CHOICES, LICENSE_CATEGORY_CHOICES

from apps.drivers.models import M_driver


class Sz_driver_in(serializers.Serializer):
    driver_id = serializers.IntegerField(required=False, allow_null=True, help_text="Vacío = crear.")
    # Usuario con el que entra a la app (al crear: uno nuevo con username/password, o user_id de Hurgo)
    user_id = serializers.IntegerField(required=False, allow_null=True)
    username = serializers.CharField(max_length=150, required=False)
    password = serializers.CharField(required=False, write_only=True)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    document_type = serializers.ChoiceField(choices=DOCUMENT_TYPE_CHOICES, required=False)
    document_number = serializers.CharField(max_length=20, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=40, required=False, allow_blank=True)
    license_number = serializers.CharField(max_length=30, required=False)
    license_category = serializers.ChoiceField(choices=LICENSE_CATEGORY_CHOICES, required=False)
    license_expedition = serializers.DateField(required=False, allow_null=True)
    license_expire = serializers.DateField(required=False, allow_null=True)
    is_available = serializers.BooleanField(required=False)
    is_active = serializers.BooleanField(required=False)


class Sz_driver(serializers.ModelSerializer):
    username = serializers.CharField(source="user_id.username", read_only=True)
    first_name = serializers.CharField(source="user_id.first_name", read_only=True)
    last_name = serializers.CharField(source="user_id.last_name", read_only=True)
    email = serializers.CharField(source="user_id.email", read_only=True)
    name = serializers.SerializerMethodField()
    document_type = serializers.SerializerMethodField()
    document_number = serializers.SerializerMethodField()
    phone = serializers.SerializerMethodField()
    license_valid = serializers.SerializerMethodField()

    class Meta:
        model = M_driver
        fields = ["id", "user_id", "username", "first_name", "last_name", "name", "email", "document_type",
                  "document_number", "phone", "license_number", "license_category", "license_expedition",
                  "license_expire", "license_valid", "average_rating", "is_available", "is_active"]

    @staticmethod
    def _detail(obj):
        return getattr(obj.user_id, "user_detail_user_id", None)  # puede no tener detalle

    def get_name(self, obj):
        return str(obj)

    def get_document_type(self, obj):
        detail = self._detail(obj)
        return detail.document_type if detail else "CC"

    def get_document_number(self, obj):
        detail = self._detail(obj)
        return detail.document_number if detail else ""

    def get_phone(self, obj):
        detail = self._detail(obj)
        return detail.phone if detail else ""

    def get_license_valid(self, obj):
        return obj.license_expire is None or obj.license_expire >= timezone.localdate()
