from django.apps import AppConfig


class DriversConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.drivers"
    label = "drivers"
    verbose_name = "Conductores"

    def ready(self):
        # Importar los steps para registrarlos en el motor
        import apps.drivers.steps.stp_driver  # noqa: F401
