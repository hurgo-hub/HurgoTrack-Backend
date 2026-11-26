from django.apps import AppConfig


class CompaniesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.companies"
    label = "companies"
    verbose_name = "Empresas y sus usuarios"

    def ready(self):
        # Importar los steps para registrarlos en el motor
        import apps.companies.steps.stp_company  # noqa: F401
