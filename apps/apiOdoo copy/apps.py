from django.apps import AppConfig


class ApiOdooConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.apiOdoo"
    label = "apiOdoo"
    verbose_name = "Integración con Odoo"

    def ready(self):
        # Importar los steps para registrarlos en el motor
        import apps.apiOdoo.steps.stp_apiOdoo  # noqa: F401
