from django.apps import AppConfig


class ApiSatrackConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.apiSatrack"
    label = "apiSatrack"
    verbose_name = "Integración con Satrack"

    def ready(self):
        # Importar los steps para registrarlos en el motor
        import apps.apiSatrack.steps.stp_apiSatrack  # noqa: F401
