from django.db import transaction

from enginedj.base.exceptions import BusinessError, BusinessNotFound, BusinessPermissionError
from enginedj.base.models import M_company
from enginedj.base.services import BaseService
from enginedj.base.services.permissions import has_perm, require_perm

from apps.locations.entity import E_address
from apps.locations.models import M_address, M_location
from apps.locations.repository import R_address, R_loading_tag

MANAGE_PERM = "locations.manage_loading_point"


class S_address(BaseService[E_address]):

    def __init__(self):
        super().__init__(repository=R_address(), entity_class=E_address)
        self.repository: R_address = self.repository
        self.r_tag = R_loading_tag()

    def recipients(self, user, query: str = ""):
        """Destinatarios con sus direcciones, para armar pedidos."""
        if not (has_perm(user, "orders.add_m_order") or has_perm(user, "trips.build_trip")):
            raise BusinessPermissionError("Solo comerciales y despacho consultan destinatarios.")
        return self.repository.recipients((query or "").strip())

    # ------------------------------------------------------------------
    # Lugares de cargue (los registra y elige Hurgo)
    # ------------------------------------------------------------------
    @staticmethod
    def _require_dispatch(user):
        if not (has_perm(user, MANAGE_PERM) or has_perm(user, "trips.build_trip") or has_perm(user, "orders.confirm_order")):
            raise BusinessPermissionError("Solo el equipo de Hurgo consulta los lugares de cargue.")

    def loading_points(self, user, *, company_id=None, tag_ids=None, item_ids=None, order_id=None, query=""):
        """Lugares de cargue. Con ``item_ids`` u ``order_id`` marca como sugeridos los que tienen
        alguna etiqueta de esos productos (``suggested`` + ``matching_tags``) y los pone primero."""
        self._require_dispatch(user)
        wanted = self._tags_of_items(item_ids, order_id)
        points = self.repository.loading_points(company_id=company_id, tag_ids=tag_ids, query=(query or "").strip())
        for point in points:
            point.matching_tags = sorted(t.name for t in point.tags.all() if t.pk in wanted)
            point.suggested = bool(point.matching_tags)
        points.sort(key=lambda p: (not p.suggested, p.name))
        return points

    @staticmethod
    def _tags_of_items(item_ids, order_id) -> set[int]:
        from apps.locations.models import M_loading_tag
        from apps.orders.models import M_order_line

        ids = set(item_ids or [])
        if order_id:
            ids |= set(M_order_line.objects.filter(order_id=order_id, is_active=True).values_list("item_id", flat=True))
        if not ids:
            return set()
        return set(M_loading_tag.objects.filter(item_loading_tags__in=ids).values_list("pk", flat=True))

    @transaction.atomic
    def save_loading_point(self, user, data: dict):
        """Crea o actualiza un lugar de cargue de cualquier empresa (planta, bodega, proveedor)."""
        require_perm(user, MANAGE_PERM, "Solo el equipo de despacho registra lugares de cargue.")
        company = M_company.objects.filter(pk=data["company_id"], is_active=True).first()
        if company is None:
            raise BusinessNotFound("La empresa dueña del lugar de cargue no existe.")
        location = M_location.objects.filter(pk=data["location_id"], is_active=True).first()
        if location is None:
            raise BusinessNotFound("El municipio no existe.")

        if data.get("address_id"):
            address = self.repository.get_for_update(data["address_id"])
            if address is None:
                raise BusinessNotFound("La dirección no existe.")
        else:
            address = M_address()
        address.company_id = company
        address.location_id = location
        address.is_loading_point = True
        for field in ("name", "address", "description", "contact_name", "contact_phone"):
            if field in data:
                setattr(address, field, data[field] or "")
        for field in ("latitude", "longitude"):
            if field in data:
                setattr(address, field, data[field])
        if "is_active" in data:
            address.is_active = data["is_active"]

        tags = None
        if "tag_ids" in data:
            found = self.r_tag.active_by_ids(set(data["tag_ids"]))
            missing = set(data["tag_ids"]) - set(found)
            if missing:
                raise BusinessNotFound(f"Etiquetas inexistentes: {sorted(missing)}.")
            tags = list(found.values())
        return self.repository.save_address(address, user, tags=tags)

    def get_loading_point(self, address_id) -> M_address:
        address = self.repository.get_active(address_id)
        if address is None or not address.is_loading_point:
            raise BusinessError("La dirección no es un lugar de cargue registrado.", code="not_loading_point")
        return address

    # ------------------------------------------------------------------
    # Etiquetas de cargue
    # ------------------------------------------------------------------
    def tags(self, user, query: str = ""):
        self._require_dispatch(user)
        return self.r_tag.active((query or "").strip())

    def create_tag(self, user, name: str):
        require_perm(user, MANAGE_PERM, "Solo el equipo de despacho crea etiquetas de cargue.")
        name = (name or "").strip()
        if not name:
            raise BusinessError("Indica el nombre de la etiqueta.")
        if self.r_tag.get_by_name(name):
            raise BusinessError(f"La etiqueta '{name}' ya existe.", code="duplicate_tag")
        return self.r_tag.create_tag(name, user)

    # ------------------------------------------------------------------
    # Listas para formularios
    # ------------------------------------------------------------------
    def lookups(self, user):
        self._require_dispatch(user)
        companies = M_company.objects.filter(is_active=True).order_by("name").values(
            "id", "name", "is_client", "is_recipient", "is_carrier")
        municipalities = M_location.objects.filter(is_active=True, location_type="municipality").select_related(
            "parent_id").order_by("name")
        return {
            "companies": list(companies),
            "municipalities": [
                {"id": m.id, "name": f"{m.name} ({m.parent_id.name})" if m.parent_id_id else m.name}
                for m in municipalities
            ],
        }
