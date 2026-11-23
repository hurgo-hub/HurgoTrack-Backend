from enginedj.base.services import BaseService

from apps.core.exceptions import BusinessError
from apps.trips.entity import E_trip_attach
from apps.trips.repository import R_trip_attach, R_trip_type_attach


class S_trip_attach(BaseService[E_trip_attach]):

    def __init__(self):
        super().__init__(repository=R_trip_attach(), entity_class=E_trip_attach)
        self.repository: R_trip_attach = self.repository

    @staticmethod
    def attach_type(key):
        attach_type = R_trip_type_attach().get_by_key(key)
        if attach_type is None:
            raise BusinessError(f"Falta el tipo de adjunto '{key}'. Ejecuta: python manage.py seed_hurgo",
                                code="missing_attach_type")
        return attach_type

    def attach_files(self, trip, user, files, type_key, line=None, event=None, latitude=None, longitude=None):
        attach_type = self.attach_type(type_key)
        return [
            self.repository.attach(trip, file, attach_type, user, line=line, event=event,
                                   latitude=latitude, longitude=longitude)
            for file in files or []
        ]
