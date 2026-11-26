"""Steps de empresas. Cada uno es un workflow: POST /api/workflows/sync/<nombre>/."""

from enginedj.base.steps.helpers import context_user, results, validate_input
from enginedj.modules.registry import register_module

from apps.companies.serializers import (
    Sz_company,
    Sz_company_create_in,
    Sz_company_id_in,
    Sz_company_update_in,
    Sz_company_user_in,
)
from apps.companies.services import S_company


@register_module("companies.create", important=True)
def create_company(context, params, execution):
    """Administración de Hurgo crea la empresa y (opcional) su usuario administrador."""
    data = validate_input(Sz_company_create_in, context)
    company, admin = S_company().create(context_user(context), company=data["company"], admin=data.get("admin"))
    return results({**Sz_company(company).data, "admin": S_company._user_row(admin) if admin else None})


@register_module("companies.update", important=True)
def update_company(context, params, execution):
    data = validate_input(Sz_company_update_in, context)
    company_id = data.pop("company_id")
    return results(Sz_company(S_company().update(context_user(context), company_id, data)).data)


@register_module("companies.list", important=True)
def list_companies(context, params, execution):
    return results(Sz_company(S_company().list(context_user(context)), many=True).data)


@register_module("companies.mine", important=True)
def my_companies(context, params, execution):
    """Empresas que administra el usuario, roles que puede asignar y tipos de producto."""
    return results(S_company().mine(context_user(context)))


@register_module("companies.users", important=True)
def company_users(context, params, execution):
    data = validate_input(Sz_company_id_in, context)
    return results(S_company().users(context_user(context), data["company_id"]))


@register_module("companies.user.save", important=True)
def save_company_user(context, params, execution):
    """Crea (sin user_id) o edita un usuario de la empresa con rol admin_empresa, comercial o facturador."""
    data = validate_input(Sz_company_user_in, context)
    company_id = data.pop("company_id")
    return results(S_company().save_user(context_user(context), company_id, data))


# ----------------------------------------------------------------------
# Roles y usuarios (administración de Hurgo)
# ----------------------------------------------------------------------
from rest_framework import serializers  # noqa: E402

from apps.companies.services import S_role  # noqa: E402


class Sz_role_in(serializers.Serializer):
    id = serializers.IntegerField(required=False, allow_null=True, help_text="Vacío = crear.")
    name = serializers.RegexField(r"^[\w ]{2,80}$", required=False)
    label = serializers.CharField(max_length=150, required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    scope = serializers.ChoiceField(choices=["hurgo", "company"], required=False, default="hurgo")
    permissions = serializers.ListField(child=serializers.CharField(max_length=120), required=False)
    is_active = serializers.BooleanField(required=False)


class Sz_user_in(serializers.Serializer):
    user_id = serializers.IntegerField(required=False, allow_null=True, help_text="Vacío = crear.")
    username = serializers.RegexField(r"^[\w.@+-]{3,150}$", required=False)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    password = serializers.CharField(max_length=128, required=False, allow_blank=True, write_only=True)
    roles = serializers.ListField(child=serializers.CharField(max_length=150), required=False)
    is_active = serializers.BooleanField(required=False)


@register_module("roles.list", important=True)
def list_roles(context, params, execution):
    return results(S_role().list(context_user(context)))


@register_module("roles.permissions", important=True)
def list_permissions(context, params, execution):
    """Permisos asignables por módulo; ``company_allowed`` = válido en roles de empresa."""
    return results(S_role().permissions(context_user(context)))


@register_module("roles.save", important=True)
def save_role(context, params, execution):
    """Crea o edita un rol (no de sistema) con su alcance y permisos."""
    data = validate_input(Sz_role_in, context)
    return results(S_role().save(context_user(context), data))


@register_module("users.list", important=True)
def list_users(context, params, execution):
    return results(S_role().users(context_user(context)))


@register_module("users.save", important=True)
def save_user(context, params, execution):
    """Crea o edita un usuario y le asigna roles."""
    data = validate_input(Sz_user_in, context)
    return results(S_role().save_user(context_user(context), data))
