from django.conf import settings
from django.db import models

from enginedj.base.models.model_base import M_model_base


class M_audit_base(M_model_base, models.Model):
    """Base de los modelos de Hurgo Track.

    Hereda de M_model_base del motor (create_date, update_date, is_active,
    código automático y permisos can_export / can_import / can_archive) y
    agrega quién creó y quién modificó el registro.

    Reemplaza la tabla ``base`` del .mwb (company_id, user_create_id,
    user_update_id): la auditoría va en cada tabla y la empresa dueña del
    registro se declara en cada modelo que la necesita.
    """

    create_user_id = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, editable=False,
        related_name="+", db_column="create_user_id",
    )
    update_user_id = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, editable=False,
        related_name="+", db_column="update_user_id",
    )

    class Meta:
        abstract = True


class M_catalog_base(M_audit_base, models.Model):
    """Catálogo simple con nombre único."""

    name = models.CharField(max_length=120, null=False, blank=False, unique=True)

    class Meta:
        abstract = True
        ordering = ["name"]

    def __str__(self):
        return self.name
