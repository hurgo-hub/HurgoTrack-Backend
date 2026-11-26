from rest_framework import serializers

from enginedj.base.models import M_company


class Sz_company(serializers.ModelSerializer):
    admins = serializers.SerializerMethodField()

    class Meta:
        model = M_company
        fields = ["id", "name", "document_number", "verification_digit", "email", "phone", "is_client",
                  "is_freelance", "is_active", "admins"]

    def get_admins(self, obj):
        return getattr(obj, "admins", [])


# ----------------------------------------------------------------------
# Entrada
# ----------------------------------------------------------------------
class Sz_company_data_in(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    document_number = serializers.RegexField(r"^\d{5,20}$", help_text="NIT sin dígito de verificación.")
    verification_digit = serializers.RegexField(r"^\d?$", required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(max_length=40, required=False, allow_blank=True)


class Sz_user_data_in(serializers.Serializer):
    username = serializers.RegexField(r"^[\w.@+-]{3,150}$")
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    password = serializers.CharField(max_length=128, write_only=True)


class Sz_company_create_in(serializers.Serializer):
    company = Sz_company_data_in()
    admin = Sz_user_data_in(required=False, allow_null=True, help_text="Usuario administrador de la empresa.")


class Sz_company_update_in(Sz_company_data_in):
    company_id = serializers.IntegerField()
    name = serializers.CharField(max_length=200, required=False)
    document_number = serializers.RegexField(r"^\d{5,20}$", required=False)
    is_active = serializers.BooleanField(required=False)


class Sz_company_id_in(serializers.Serializer):
    company_id = serializers.IntegerField()


class Sz_company_user_in(Sz_company_id_in):
    user_id = serializers.IntegerField(required=False, allow_null=True, help_text="Vacío = crear.")
    username = serializers.RegexField(r"^[\w.@+-]{3,150}$", required=False)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    password = serializers.CharField(max_length=128, required=False, allow_blank=True, write_only=True)
    role = serializers.CharField(max_length=40)
    is_active = serializers.BooleanField(required=False)
