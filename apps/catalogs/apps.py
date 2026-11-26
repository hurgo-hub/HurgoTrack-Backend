from django.apps import AppConfig


class CatalogsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.catalogs"
    label = "catalogs"
    verbose_name = "Catálogos (tipos, unidades, marcas...)"

    def ready(self):
        import apps.catalogs.steps.stp_catalog  # noqa: F401
