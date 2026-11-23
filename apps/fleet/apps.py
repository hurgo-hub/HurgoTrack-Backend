from django.apps import AppConfig


class FleetConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.fleet"
    label = "fleet"
    verbose_name = "Flota"

    def ready(self):
        # Importar los steps para registrarlos en el motor
        import apps.fleet.steps.stp_vehicle  # noqa: F401
