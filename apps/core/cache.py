"""Invalidación de la caché de listados del motor.

El motor cachea ``list_with_relations_m2m`` por modelo y solo lo invalida
cuando se escribe con su repositorio genérico. Los servicios de Hurgo
escriben con el ORM, así que invalidan aquí al terminar cada acción.
"""

from django.apps import apps

from enginedj.base.cache import LIST_WITH_RELATIONS_M2M, invalidate_on_commit, model_namespace


def invalidate_apps(*app_labels: str):
    for app_label in app_labels:
        for model in apps.get_app_config(app_label).get_models():
            invalidate_on_commit(model_namespace(model), LIST_WITH_RELATIONS_M2M)


class InvalidateAppsMixin:
    """Para repositorios de pedidos y viajes: un listado de viajes trae paradas, eventos y pedidos
    como relaciones, así que cualquier escritura invalida los listados de ambas apps."""

    invalidate_app_labels = ("orders", "trips")

    def _invalidate_list_cache(self):
        if getattr(self, "cache_enabled", True):
            invalidate_apps(*self.invalidate_app_labels)
