from django.apps import AppConfig


class OrdersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.orders"
    label = "orders"
    verbose_name = "Pedidos y productos"

    def ready(self):
        # Importar los steps para registrarlos en el motor
        import apps.orders.steps.stp_order  # noqa: F401
        import apps.orders.steps.stp_item  # noqa: F401
        import apps.orders.steps.stp_order_line  # noqa: F401
