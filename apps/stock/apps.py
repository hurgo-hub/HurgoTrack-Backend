from django.apps import AppConfig


class StockConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.stock"
    label = "stock"
    verbose_name = "Stock y solicitudes de compra"

    def ready(self):
        # Importar los steps para registrarlos en el motor
        import apps.stock.steps.stp_stock  # noqa: F401
        import apps.stock.steps.stp_purchase_request  # noqa: F401
