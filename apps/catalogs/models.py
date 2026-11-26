from django.db import models


class M_catalogs_access(models.Model):
    """Sin tabla: solo declara los permisos de gestión de catálogos."""

    class Meta:
        managed = False
        default_permissions = ()
        permissions = [
            ("manage_company_catalogs", "Puede gestionar los catálogos de su empresa (tipos, unidades, marcas)"),
            ("manage_hurgo_catalogs", "Puede gestionar los catálogos comunes y de Hurgo (etiquetas, flota)"),
        ]
