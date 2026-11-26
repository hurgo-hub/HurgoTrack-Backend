"""Listado y guardado genérico de catálogos (ver ``apps.catalogs.registry``).

La empresa solo ve y edita los suyos; Hurgo solo los de logística. Hurgo no crea tipos,
unidades, marcas ni documentos de una empresa.
"""

from django.apps import apps
from django.db import IntegrityError, transaction

from enginedj.base.exceptions import BusinessError, BusinessNotFound, BusinessPermissionError
from enginedj.base.services.permissions import has_perm, user_company_ids

from apps.catalogs.registry import CATALOGS
from apps.companies.tenancy import company_schema

HURGO_PERM = "catalogs.manage_hurgo_catalogs"
COMPANY_PERM = "catalogs.manage_company_catalogs"


def _choices(kind):
    return [o.split("=", 1) for o in kind[len("choice:"):].split(",")]


class S_catalog:

    @staticmethod
    def _catalog(key):
        catalog = CATALOGS.get(key)
        if catalog is None:
            raise BusinessNotFound(f"El catálogo '{key}' no existe.")
        return catalog, apps.get_model(catalog.model)

    @staticmethod
    def _company_for(user, company_id):
        """Empresa del usuario (la única suya si no la indica). Solo usuarios de esa empresa."""
        own = user_company_ids(user)
        if company_id is None:
            if len(own) != 1:
                raise BusinessError("Indica la empresa.", code="company_required")
            return own[0]
        if company_id not in own:
            raise BusinessPermissionError("Solo puedes gestionar los catálogos de tu empresa.")
        return company_id

    @staticmethod
    def _is_company_user(user) -> bool:
        """Pertenece a una empresa y gestiona sus catálogos (un superusuario de Hurgo no es usuario de empresa)."""
        return has_perm(user, COMPANY_PERM) and bool(user_company_ids(user))

    def _require(self, user, catalog):
        if catalog.scope == "company":
            if not self._is_company_user(user):
                raise BusinessPermissionError("Este catálogo lo gestiona cada empresa.")
        elif not has_perm(user, HURGO_PERM):
            raise BusinessPermissionError("Este catálogo lo gestiona Hurgo.")

    def available(self, user):
        """Catálogos que el usuario puede gestionar (para las pestañas)."""
        out = []
        for catalog in CATALOGS.values():
            allowed = self._is_company_user(user) if catalog.scope == "company" else has_perm(user, HURGO_PERM)
            if allowed:
                out.append({"key": catalog.key, "label": catalog.label, "scope": catalog.scope,
                            "fields": [self._field(name, kind) for name, kind in catalog.fields.items()]})
        return out

    @staticmethod
    def _field(name, kind):
        if kind.startswith("choice:"):
            return {"name": name, "kind": "choice",
                    "options": [{"value": v, "label": label} for v, label in _choices(kind)]}
        return {"name": name, "kind": kind}

    def list(self, user, key, company_id=None):
        catalog, model = self._catalog(key)
        self._require(user, catalog)
        if catalog.scope == "company":
            company = self._company_for(user, company_id)
            with company_schema(company):  # viven en el esquema de la empresa
                return [self._row(catalog, obj) for obj in model.objects.filter(company_id=company).order_by("name")]
        return [self._row(catalog, obj) for obj in model.objects.all().order_by("name")]

    @staticmethod
    def _row(catalog, obj):
        row = {"id": obj.pk, "name": obj.name, "is_active": obj.is_active, "read_only": False}
        for name in catalog.fields:
            row[name] = getattr(obj, name)
        return row

    def save(self, user, key, data: dict):
        catalog, model = self._catalog(key)
        self._require(user, catalog)
        if catalog.scope == "company":
            company_id = self._company_for(user, data.get("company_id"))
            with company_schema(company_id):
                return self._save(user, catalog, model, data, company_id)
        return self._save(user, catalog, model, data, None)

    @transaction.atomic
    def _save(self, user, catalog, model, data, company_id):
        name = (data.get("name") or "").strip()
        if not name:
            raise BusinessError("Indica el nombre.")
        owned = catalog.scope == "company"  # el modelo tiene company_id

        if data.get("id"):
            obj = model.objects.select_for_update().filter(pk=data["id"]).first()
            if obj is None or (owned and obj.company_id_id != company_id):
                raise BusinessNotFound("El registro no existe o no es tuyo.")
            obj.update_user = user
        else:
            obj = model(create_user=user)
            if owned:
                obj.company_id_id = company_id
        obj.name = name
        for field_name, kind in catalog.fields.items():
            if field_name not in data:
                continue
            value = data[field_name]
            if kind.startswith("choice:") and value not in [v for v, _ in _choices(kind)]:
                raise BusinessError(f"Valor inválido para {field_name}.")
            setattr(obj, field_name, bool(value) if kind == "bool" else (value or "").strip())
        if "is_active" in data:
            if not data["is_active"] and getattr(obj, "is_system", False):
                raise BusinessError("Este documento lo usa el sistema; no se puede desactivar.", code="system_record")
            obj.is_active = bool(data["is_active"])
        try:
            with transaction.atomic():
                obj.save()
        except IntegrityError:
            raise BusinessError(f"Ya existe '{name}' en este catálogo.", code="duplicate")
        return self._row(catalog, obj)
