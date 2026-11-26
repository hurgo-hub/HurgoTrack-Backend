from django.apps import AppConfig


class TripsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.trips"
    label = "trips"
    verbose_name = "Viajes y entregas"

    def ready(self):
        # Importar los steps para registrarlos en el motor
        import apps.trips.steps.stp_trip  # noqa: F401
        import apps.trips.steps.stp_trip_line  # noqa: F401
        import apps.trips.steps.stp_trip_line_serie  # noqa: F401
        import apps.trips.steps.stp_trip_event  # noqa: F401
        import apps.trips.steps.stp_document  # noqa: F401
