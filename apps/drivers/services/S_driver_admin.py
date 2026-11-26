"""Gestión de conductores desde la app (administración de Hurgo).

Cada conductor es un usuario de Hurgo con el rol ``conductor`` (entra a la app a ver y entregar sus
viajes) y su licencia. Queda a nombre de la empresa Hurgo, como la flota.
"""

from django.contrib.auth.models import Group, User
from django.db import transaction

from enginedj.base.exceptions import BusinessError, BusinessNotFound
from enginedj.base.models import M_user_detail

from apps.drivers.models import M_driver
from apps.fleet.services.S_fleet import hurgo_company, require_fleet

DRIVER_ROLE = "conductor"
LICENSE_FIELDS = ("license_category", "license_expedition", "license_expire", "is_available", "is_active")


class S_driver_admin:

    def list(self, user):
        require_fleet(user, "drivers.view_m_driver", "No tienes permiso para ver los conductores.")
        return list(M_driver.objects.select_related("user_id", "user_id__user_detail_user_id")
                    .order_by("-is_active", "user_id__first_name", "user_id__username"))

    def detail(self, driver_id) -> M_driver:
        return M_driver.objects.select_related("user_id", "user_id__user_detail_user_id").get(pk=driver_id)

    @transaction.atomic
    def save(self, user, data: dict) -> M_driver:
        """Crea (sin driver_id) o edita un conductor. Al crear, con un usuario nuevo (username + password)
        o con ``user_id`` de un usuario de Hurgo que aún no es conductor."""
        number = None
        if "license_number" in data:
            number = "".join(ch for ch in data["license_number"].upper() if ch.isalnum())
            if M_driver.objects.filter(license_number=number).exclude(pk=data.get("driver_id")).exists():
                raise BusinessError(f"Ya existe un conductor con la licencia {number}.", code="duplicate_license")
        if data.get("driver_id"):
            require_fleet(user, "drivers.change_m_driver", "No tienes permiso para editar conductores.")
            driver = M_driver.objects.select_for_update().select_related("user_id").filter(pk=data["driver_id"]).first()
            if driver is None:
                raise BusinessNotFound("El conductor no existe.")
            driver.update_user = user
            target = driver.user_id
            self._update_user(user, target, data)
        else:
            require_fleet(user, "drivers.add_m_driver", "No tienes permiso para registrar conductores.")
            if not data.get("license_number") or not data.get("license_category"):
                raise BusinessError("Indica el número y la categoría de la licencia.", code="invalid_input")
            target = self._user_for_new_driver(user, data)
            driver = M_driver(company_id=hurgo_company(), user_id=target, create_user=user)
        if number is not None:
            driver.license_number = number
        for field in LICENSE_FIELDS:
            if field in data:
                setattr(driver, field, data[field])
        driver.save()
        self._save_detail(target, data, user)
        return driver

    # ------------------------------------------------------------------
    @staticmethod
    def _user_for_new_driver(user, data):
        from apps.companies.services.S_role import S_role

        if data.get("user_id"):
            target = S_role._hurgo_users().filter(pk=data["user_id"], is_active=True).first()
            if target is None:
                raise BusinessNotFound("El usuario no existe, está inactivo o es de una empresa.")
            if M_driver.objects.filter(user_id=target).exists():
                raise BusinessError(f"{target.username} ya es conductor.", code="duplicate_driver")
            target.groups.add(Group.objects.get(name=DRIVER_ROLE))
            return target
        row = S_role().save_user(user, {
            "username": data.get("username"), "password": data.get("password"), "roles": [DRIVER_ROLE],
            **{k: data[k] for k in ("first_name", "last_name", "email") if k in data},
        })
        return User.objects.get(pk=row["id"])

    @staticmethod
    def _update_user(user, target, data):
        from apps.companies.services.S_company import S_company

        for field in ("first_name", "last_name", "email"):
            if field in data:
                setattr(target, field, (data[field] or "").strip())
        if data.get("password"):
            S_company._check_password(data["password"], target)
            target.set_password(data["password"])
        target.save()

    @staticmethod
    def _save_detail(target, data, user):
        if not any(k in data for k in ("document_type", "document_number", "phone")):
            return
        detail, _ = M_user_detail.objects.get_or_create(user_id=target, defaults={"create_user": user})
        for field in ("document_type", "document_number", "phone"):
            if field in data:
                setattr(detail, field, (data[field] or "").strip())
        detail.save()
