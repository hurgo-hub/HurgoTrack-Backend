"""Documentos requeridos por etapa (``M_trip_type_attach.stage`` / ``is_required``).

Aplican los de la empresa del pedido o viaje y los de Hurgo (``company_id`` nulo):
- ``order``: subidos al pedido (``M_order_attach``) antes de confirmarlo.
- ``loading``: subidos al viaje antes de salir a ruta.
- ``delivery``: subidos a la parada antes de entregar (la remisión llega con la entrega).
"""

from django.db import transaction
from django.db.models import Q

from enginedj.base.exceptions import BusinessError, BusinessNotFound, BusinessPermissionError
from enginedj.base.services.permissions import has_perm

from apps.trips.models import M_trip_attach, M_trip_type_attach


def types_for(company_id, stage):
    return M_trip_type_attach.objects.filter(
        Q(company_id=company_id) | Q(company_id__isnull=True), stage=stage, is_active=True
    ).order_by("-is_required", "name")


def _missing(types, present_ids):
    return [t.name for t in types if t.is_required and t.pk not in present_ids]


def require_order_documents(order):
    from apps.orders.models import M_order_attach

    present = set(M_order_attach.objects.filter(order_id=order, is_active=True).values_list("type_attach_id", flat=True))
    missing = _missing(types_for(order.company_id_id, "order"), present)
    if missing:
        raise BusinessError(f"Faltan documentos del pedido: {', '.join(missing)}.", code="missing_documents")


def require_loading_documents(trip):
    present = set(M_trip_attach.objects.filter(trip_id=trip, is_active=True).values_list("type_attach_id", flat=True))
    missing = _missing(types_for(trip.company_id_id, "loading"), present)
    if missing:
        raise BusinessError(f"Faltan documentos de cargue: {', '.join(missing)}.", code="missing_documents")


def require_delivery_documents(trip, stop):
    present = set(M_trip_attach.objects.filter(trip_line_id=stop, is_active=True).values_list("type_attach_id",
                                                                                                flat=True))
    types = [t for t in types_for(trip.company_id_id, "delivery") if not t.is_delivery_proof]
    missing = _missing(types, present)
    if missing:
        raise BusinessError(f"Parada {stop.sequence}: faltan documentos de entrega: {', '.join(missing)}.",
                            code="missing_documents")


def _type(type_id, company_id, stages):
    doc_type = M_trip_type_attach.objects.filter(
        Q(company_id=company_id) | Q(company_id__isnull=True), pk=type_id, is_active=True, stage__in=stages
    ).first()
    if doc_type is None:
        raise BusinessNotFound("El tipo de documento no existe, es de otra empresa o no aplica en esta etapa.")
    return doc_type


def _file_row(a):
    return {"id": a.id, "name": a.file.name.rsplit("/", 1)[-1], "create_date": a.create_date}


class S_document:

    # ------------------------------------------------------------------
    # Pedido
    # ------------------------------------------------------------------
    def order_documents(self, user, order_id):
        from apps.orders.services import S_order

        order = S_order().detail(user, order_id)  # valida que lo pueda ver
        files = {}
        for a in order.order_attach_order_id.filter(is_active=True).order_by("id"):
            files.setdefault(a.type_attach_id_id, []).append(_file_row(a))
        return [{"id": t.id, "name": t.name, "is_required": t.is_required, "files": files.get(t.id, [])}
                for t in types_for(order.company_id_id, "order")]

    @transaction.atomic
    def attach_order(self, user, order_id, type_id, files):
        from apps.orders.models import M_order_attach
        from apps.orders.services import S_order

        s_order = S_order()
        order = s_order._lock(order_id)
        if not (has_perm(user, "orders.confirm_order") or s_order.can_manage_company(user, order.company_id_id)):
            raise BusinessPermissionError("No puedes subir documentos a este pedido.")
        if order.state in ("delivered", "cancelled"):
            raise BusinessError(f"El pedido {order.code} ya está '{order.get_state_display()}'.", code="invalid_state")
        if not files:
            raise BusinessError("Adjunta al menos un archivo.")
        doc_type = _type(type_id, order.company_id_id, ["order"])
        for file in files:
            M_order_attach.objects.create(order_id=order, type_attach_id=doc_type, file=file, create_user=user)
        s_order.r_event.register(order, user, "Documento subido", description=doc_type.name)
        return order

    # ------------------------------------------------------------------
    # Viaje (cargue y entrega)
    # ------------------------------------------------------------------
    def trip_documents(self, user, trip_id):
        from apps.trips.services import S_trip

        trip = S_trip().detail(user, trip_id)
        attachments = list(M_trip_attach.objects.filter(trip_id=trip, is_active=True).order_by("id"))

        def files(type_id, stop_id=None):
            return [_file_row(a) for a in attachments
                    if a.type_attach_id_id == type_id and (stop_id is None or a.trip_line_id_id == stop_id)]

        loading = [{"id": t.id, "name": t.name, "is_required": t.is_required, "files": files(t.id)}
                   for t in types_for(trip.company_id_id, "loading")]
        delivery_types = [t for t in types_for(trip.company_id_id, "delivery") if not t.is_delivery_proof]
        stops = [
            {"trip_line_id": s.id, "sequence": s.sequence,
             "documents": [{"id": t.id, "name": t.name, "is_required": t.is_required, "files": files(t.id, s.id)}
                           for t in delivery_types]}
            for s in trip.trip_line_trip_id.all().order_by("sequence")
        ]
        return {"loading": loading, "delivery": stops}

    @transaction.atomic
    def attach_trip(self, user, trip_id, type_id, files, trip_line_id=None):
        from apps.trips.services import S_trip
        from apps.trips.services.S_trip_attach import S_trip_attach

        s_trip = S_trip()
        trip = s_trip.lock(trip_id)
        is_driver = trip.driver_id_id and trip.driver_id.user_id_id == getattr(user, "id", None)
        if not (has_perm(user, "trips.build_trip") or is_driver):
            raise BusinessPermissionError("Solo despacho o el conductor asignado suben documentos del viaje.")
        if trip.state in ("closed", "cancelled"):
            raise BusinessError(f"El viaje {trip.code} ya está '{trip.get_state_display()}'.", code="invalid_state")
        if not files:
            raise BusinessError("Adjunta al menos un archivo.")
        doc_type = _type(type_id, trip.company_id_id, ["loading", "delivery"])
        stop = None
        if doc_type.stage == "delivery":
            stop = s_trip.r_line.get_for_update(trip, trip_line_id) if trip_line_id else None
            if stop is None:
                raise BusinessError("Indica la parada del documento de entrega.", code="stop_required")
        repository = S_trip_attach().repository
        for file in files:
            repository.attach(trip, file, doc_type, user, line=stop)
        s_trip.events.register(trip, user, "Documento subido", event_type="comment", line=stop,
                               description=doc_type.name)
        return trip
