"""Documentos requeridos por etapa.

Dos orígenes (cada uno en su esquema):
- **Hurgo** (central, ``trips.M_trip_type_attach``): documentos del proceso (foto de cargue, remisión...),
  con archivos en ``trips.M_trip_attach``.
- **Empresa** (su esquema, ``orders.M_document_type``): lo que exige cada empresa, con archivos en
  ``orders.M_document_file``.

Etapas: ``order`` (para confirmar el pedido; solo de la empresa), ``loading`` (antes de salir),
``delivery`` (antes de entregar; la remisión llega con la entrega). Los steps corren en el esquema de
la empresa del pedido o del viaje, así que aquí se leen ambos orígenes.
Cada documento se identifica con ``key`` = ``"hurgo:<id>"`` o ``"company:<id>"``.
"""

from django.db import transaction

from enginedj.base.exceptions import BusinessError, BusinessNotFound, BusinessPermissionError
from enginedj.base.services.permissions import has_perm

from apps.companies.uploads import display_name
from apps.trips.models import M_trip_attach, M_trip_type_attach


def hurgo_types(stage):
    return list(M_trip_type_attach.objects.filter(stage=stage, is_active=True).order_by("-is_required", "name"))


def company_types(company_id, stage):
    from apps.orders.models import M_document_type

    return list(M_document_type.objects.filter(company_id=company_id, stage=stage, is_active=True)
                .order_by("-is_required", "name"))


def _missing(types, present_ids):
    return [t.name for t in types if t.is_required and t.pk not in present_ids]


def _company_files(**filters):
    from apps.orders.models import M_document_file

    return M_document_file.objects.filter(is_active=True, **filters)


def require_order_documents(order):
    present = set(_company_files(order_id=order).values_list("document_type_id", flat=True))
    missing = _missing(company_types(order.company_id_id, "order"), present)
    if missing:
        raise BusinessError(f"Faltan documentos del pedido: {', '.join(missing)}.", code="missing_documents")


def require_loading_documents(trip):
    hurgo_present = set(M_trip_attach.objects.filter(trip_id=trip, is_active=True)
                        .values_list("type_attach_id", flat=True))
    company_present = set(_company_files(trip_id=trip, trip_line_id__isnull=True)
                          .values_list("document_type_id", flat=True))
    missing = (_missing(hurgo_types("loading"), hurgo_present)
               + _missing(company_types(trip.company_id_id, "loading"), company_present))
    if missing:
        raise BusinessError(f"Faltan documentos de cargue: {', '.join(missing)}.", code="missing_documents")


def require_delivery_documents(trip, stop):
    hurgo_present = set(M_trip_attach.objects.filter(trip_line_id=stop, is_active=True)
                        .values_list("type_attach_id", flat=True))
    company_present = set(_company_files(trip_line_id=stop).values_list("document_type_id", flat=True))
    missing = (_missing([t for t in hurgo_types("delivery") if not t.is_delivery_proof], hurgo_present)
               + _missing(company_types(trip.company_id_id, "delivery"), company_present))
    if missing:
        raise BusinessError(f"Parada {stop.sequence}: faltan documentos de entrega: {', '.join(missing)}.",
                            code="missing_documents")


def _file_row(a):
    return {"id": a.id, "name": display_name(a.file), "create_date": a.create_date}


def _row(kind, doc_type, files):
    return {"key": f"{kind}:{doc_type.pk}", "id": doc_type.pk, "source": kind, "name": doc_type.name,
            "is_required": doc_type.is_required, "files": files}


def _parse_key(key):
    kind, _, raw = (key or "").partition(":")
    if kind not in ("hurgo", "company") or not raw.isdigit():
        raise BusinessError("Documento inválido.", code="invalid_document")
    return kind, int(raw)


class S_document:

    # ------------------------------------------------------------------
    # Pedido (solo documentos de la empresa)
    # ------------------------------------------------------------------
    def order_documents(self, user, order_id):
        from apps.orders.services import S_order

        order = S_order().detail(user, order_id)  # valida que lo pueda ver
        files = {}
        for a in _company_files(order_id=order).order_by("id"):
            files.setdefault(a.document_type_id_id, []).append(_file_row(a))
        return [_row("company", t, files.get(t.pk, [])) for t in company_types(order.company_id_id, "order")]

    @transaction.atomic
    def attach_order(self, user, order_id, key, files):
        from apps.orders.models import M_document_file, M_document_type
        from apps.orders.services import S_order

        s_order = S_order()
        order = s_order._lock(order_id)
        if not (has_perm(user, "orders.confirm_order") or s_order.can_manage_company(user, order.company_id_id)):
            raise BusinessPermissionError("No puedes subir documentos a este pedido.")
        if order.state in ("delivered", "cancelled"):
            raise BusinessError(f"El pedido {order.code} ya está '{order.get_state_display()}'.", code="invalid_state")
        if not files:
            raise BusinessError("Adjunta al menos un archivo.")
        kind, type_id = _parse_key(key)
        doc_type = M_document_type.objects.filter(pk=type_id, stage="order", is_active=True).first() \
            if kind == "company" else None
        if doc_type is None:
            raise BusinessNotFound("El tipo de documento no existe o no aplica al pedido.")
        for file in files:
            M_document_file.objects.create(document_type_id=doc_type, order_id=order, file=file, create_user=user)
        s_order.r_event.register(order, user, "Documento subido", description=doc_type.name)
        return order

    # ------------------------------------------------------------------
    # Viaje (cargue y entrega): de Hurgo y de la empresa
    # ------------------------------------------------------------------
    def trip_documents(self, user, trip_id):
        from apps.trips.services import S_trip

        trip = S_trip().detail(user, trip_id)
        hurgo_files = list(M_trip_attach.objects.filter(trip_id=trip, is_active=True).order_by("id"))
        company_files = list(_company_files(trip_id=trip).order_by("id"))

        def hurgo(t, stop_id=None):
            return [_file_row(a) for a in hurgo_files
                    if a.type_attach_id_id == t.pk and (stop_id is None or a.trip_line_id_id == stop_id)]

        def company(t, stop_id=None):
            return [_file_row(a) for a in company_files
                    if a.document_type_id_id == t.pk and a.trip_line_id_id == stop_id]

        loading = ([_row("hurgo", t, hurgo(t)) for t in hurgo_types("loading")]
                   + [_row("company", t, company(t)) for t in company_types(trip.company_id_id, "loading")])
        h_delivery = [t for t in hurgo_types("delivery") if not t.is_delivery_proof]
        c_delivery = company_types(trip.company_id_id, "delivery")
        stops = [
            {"trip_line_id": s.id, "sequence": s.sequence,
             "documents": [_row("hurgo", t, hurgo(t, s.id)) for t in h_delivery]
             + [_row("company", t, company(t, s.id)) for t in c_delivery]}
            for s in trip.trip_line_trip_id.all().order_by("sequence")
        ]
        return {"loading": loading, "delivery": stops}

    @transaction.atomic
    def attach_trip(self, user, trip_id, key, files, trip_line_id=None):
        from apps.orders.models import M_document_file, M_document_type
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
        kind, type_id = _parse_key(key)
        if kind == "hurgo":
            doc_type = M_trip_type_attach.objects.filter(pk=type_id, is_active=True,
                                                         stage__in=["loading", "delivery"]).first()
        else:
            doc_type = M_document_type.objects.filter(pk=type_id, company_id=trip.company_id_id, is_active=True,
                                                      stage__in=["loading", "delivery"]).first()
        if doc_type is None:
            raise BusinessNotFound("El tipo de documento no existe o no aplica en esta etapa.")
        stop = None
        if doc_type.stage == "delivery":
            stop = s_trip.r_line.get_for_update(trip, trip_line_id) if trip_line_id else None
            if stop is None:
                raise BusinessError("Indica la parada del documento de entrega.", code="stop_required")
        for file in files:
            if kind == "hurgo":
                S_trip_attach().repository.attach(trip, file, doc_type, user, line=stop)
            else:
                M_document_file.objects.create(document_type_id=doc_type, trip_id=trip, trip_line_id=stop, file=file,
                                               create_user=user)
        s_trip.events.register(trip, user, "Documento subido", event_type="comment", line=stop,
                               description=doc_type.name)
        return trip
