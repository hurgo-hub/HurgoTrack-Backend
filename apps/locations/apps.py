from django.apps import AppConfig


class LocationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.locations"
    label = "locations"
    verbose_name = "Direcciones"

    def ready(self):
        # Importar los steps para registrarlos en el motor
        import apps.locations.steps.stp_address  # noqa: F401
