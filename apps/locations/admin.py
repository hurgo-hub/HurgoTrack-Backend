from django.apps import apps
from django.contrib import admin

from apps.locations.models import M_country, M_location


class ReadOnlyAdmin(admin.ModelAdmin):
    """Datos oficiales (DIVIPOLA del DANE): se cargan con seed_workflows; nadie los crea ni los edita."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(M_country, ReadOnlyAdmin)
admin.site.register(M_location, ReadOnlyAdmin)
for model in apps.get_app_config("locations").get_models():
    if model not in (M_country, M_location):
        admin.site.register(model)
