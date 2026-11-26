from django.db import models
from django_tenants.models import DomainMixin, TenantMixin


class M_tenant(TenantMixin):
    """Esquema de PostgreSQL de una empresa (``c<id>``), creado al dar de alta la empresa.

    Ahí viven sus catálogos, productos, direcciones, pedidos, documentos, compras y stock.
    Hurgo y las demás empresas no comparten esas tablas. El esquema no se borra al
    desactivar la empresa (``auto_drop_schema = False``).
    """

    company = models.OneToOneField("base.M_company", on_delete=models.PROTECT, related_name="tenant",
                                   db_column="company_id")
    create_date = models.DateTimeField(auto_now_add=True)

    auto_create_schema = True
    auto_drop_schema = False

    def __str__(self):
        return self.schema_name

    class Meta:
        db_table = "company_tenant"


class M_domain(DomainMixin):
    """Requerido por django-tenants; Hurgo Track no enruta por dominio (todo va por la misma API)."""

    class Meta:
        db_table = "company_tenant_domain"
