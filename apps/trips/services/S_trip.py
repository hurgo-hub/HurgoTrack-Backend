"""Reglas del viaje (pasos 3, 4 y 8 del documento).

3. Arma el viaje -> build / add_allocations / assign / cancel     (despacho)
4. Salida        -> depart                                        (conductor asignado)
8. Cierre        -> close_if_done (automático)
   Devolución    -> create_return_trip                            (despacho)

Las paradas (pasos 5 y 7) están en S_trip_line, los VIN en S_trip_line_serie
y las novedades (paso 6) en S_trip_event.
"""

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from enginedj.base.services import BaseService

from enginedj.base.repository import R_company
from enginedj.base.exceptions import BusinessError, BusinessNotFound, BusinessPermissionError
from enginedj.base.services.permissions import has_perm, require_perm, user_company_ids
from apps.locations.repository import R_address
from apps.orders.repository import R_order_line, R_order_line_trip
from apps.orders.services import S_order_line
from apps.stock.services import S_stock
from apps.trips.entity import E_trip
from apps.trips.repository import R_trip, R_trip_line, R_trip_line_serie
from apps.trips.services.S_trip_event import S_trip_event

EDITABLE_STATES = ("draft", "assigned")
ON_ROUTE_STATES = ("in_route", "delivering")


class S_trip(BaseService[E_trip]):

    def __init__(self):
        super().__init__(repository=R_trip(), entity_class=E_trip)
        self.repository: R_trip = self.repository
        self.r_line = R_trip_line()
        self.r_allocation = R_order_line_trip()
        self.events = S_trip_event()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def lock(self, trip_id):
        trip = self.repository.get_for_update(trip_id)
        if trip is None:
            raise BusinessNotFound("El viaje no existe.")
        return trip

    @staticmethod
    def require_state(trip, states, action):
        if trip.state not in states:
            raise BusinessError(
                f"No se puede {action}: el viaje {trip.code} está '{trip.get_state_display()}'.",
                code="invalid_state",
            )

    @staticmethod
    def require_driver(trip, user):
        """Solo el conductor asignado; ni despacho ni un superusuario lo reemplazan."""
        from apps.drivers.services import S_driver

        if not has_perm(user, "trips.drive_trip") or not S_driver().is_user(trip.driver_id_id, user):
            raise BusinessPermissionError("Solo el conductor asignado al viaje puede hacer esta acción.")

    def set_state(self, trip, user, new_state, name, **event_kwargs):
        old_state = self.repository.set_state(trip, new_state, user)
        return self.events.register(trip, user, name, from_state=old_state, to_state=new_state, **event_kwargs)

    # ------------------------------------------------------------------
    # 3. Armar el viaje
    # ------------------------------------------------------------------
    @transaction.atomic
    def build(self, user, *, company_id, allocations, origin_address_id=None, planned_departure=None, notes=""):
        """Crea el viaje con las líneas de pedido: [{"order_line_id", "qty"}]. Una parada por destino.

        Un solo lugar de cargue por viaje: ``origin_address_id`` o, si no se envía, el lugar de
        cargue que Hurgo eligió en los pedidos (debe ser el mismo para todos).
        """
        require_perm(user, "trips.build_trip", "Solo el equipo de despacho puede armar viajes.")
        if not allocations:
            raise BusinessError("El viaje debe llevar al menos una línea de pedido.")
        company = R_company().get_active(company_id)
        if company is None:
            raise BusinessNotFound("La empresa no existe.")
        if origin_address_id is None:
            origin_address_id = self._loading_point_of(allocations)
        origin = R_address().get_active(origin_address_id)
        if origin is None:
            raise BusinessNotFound("La dirección de origen no existe.")
        if not origin.is_loading_point and origin.company_id_id != company.pk:
            raise BusinessError(f"'{origin.name}' no es un lugar de cargue registrado.", code="not_loading_point")

        trip = self.repository.create_trip(company_id=company, origin_address_id=origin,
                                           planned_departure=planned_departure, notes=notes or "",
                                           create_user=user)
        self.events.register(trip, user, "Viaje armado", to_state="draft")
        self._allocate(trip, user, allocations)
        return trip

    @transaction.atomic
    def add_allocations(self, user, trip_id, allocations):
        require_perm(user, "trips.build_trip", "Solo el equipo de despacho puede armar viajes.")
        trip = self.lock(trip_id)
        if not allocations:
            raise BusinessError("Indica al menos una línea de pedido.")
        self._allocate(trip, user, allocations)
        return trip

    @staticmethod
    def _loading_point_of(allocations):
        ids = {int(a["order_line_id"]) for a in allocations}
        points = {line.order_id.address_id_id for line in R_order_line().with_order_and_item(ids)}
        points.discard(None)
        if not points:
            raise BusinessError("Indica el lugar de cargue del viaje (los pedidos aún no lo tienen).",
                                code="loading_point_required")
        if len(points) > 1:
            raise BusinessError("Los pedidos cargan en lugares distintos: arma un viaje por lugar de cargue.",
                                code="mixed_loading_point")
        return points.pop()

    def _allocate(self, trip, user, allocations):
        self.require_state(trip, ("draft",), "agregar pedidos (solo mientras se arma)")
        requested: dict[int, Decimal] = {}
        for allocation in allocations:
            qty = allocation["qty"] if isinstance(allocation["qty"], Decimal) else Decimal(str(allocation["qty"]))
            if qty <= 0:
                raise BusinessError("La cantidad a despachar debe ser mayor que cero.")
            line_id = int(allocation["order_line_id"])
            requested[line_id] = requested.get(line_id, Decimal("0")) + qty

        r_order_line = R_order_line()
        # Bloquea las líneas para que dos viajes no asignen la misma cantidad a la vez.
        missing = set(requested) - r_order_line.lock_active(requested)
        if missing:
            raise BusinessNotFound(f"Líneas de pedido inexistentes: {sorted(missing)}.")
        order_lines = r_order_line.with_order_and_item(requested)

        for line in order_lines:
            order, qty = line.order_id, requested[line.pk]
            if order.company_id_id != trip.company_id_id:
                raise BusinessError(f"El pedido {order.code} es de otra empresa; un viaje lleva carga de una sola "
                                    "empresa.", code="mixed_company")
            if order.state not in ("confirmed", "in_progress"):
                raise BusinessError(f"El pedido {order.code} no está confirmado.", code="order_not_confirmed")
            if line.state == "cancelled":
                raise BusinessError(f"La línea de {line.item_id} del pedido {order.code} está cancelada.")
            if qty > line.qty_pending:
                raise BusinessError(f"{line.item_id} del pedido {order.code}: pides {qty} y solo quedan "
                                    f"{line.qty_pending} por asignar.", code="qty_exceeded")
            if line.item_id.is_serialized and qty != qty.to_integral_value():
                raise BusinessError(f"{line.item_id} se despacha por unidades enteras.")
            if order.address_id_id and order.address_id_id != trip.origin_address_id_id:
                raise BusinessError(f"El pedido {order.code} carga en '{order.address_id}'; un viaje tiene un solo "
                                    "lugar de cargue.", code="mixed_loading_point")

        self._check_single_brand(trip, user, [line.item_id for line in order_lines])

        stops = self.r_line.stops_by_destination(trip)
        next_sequence = self.repository.next_sequence(trip)
        for line in order_lines:
            qty = requested[line.pk]
            key = (line.recipient_id_id, line.address_id_id)
            stop = stops.get(key)
            if stop is None:
                stop = self.r_line.create_stop(trip_id=trip, sequence=next_sequence, recipient_id_id=key[0],
                                               address_id_id=key[1], create_user=user)
                stops[key] = stop
                next_sequence += 1
            allocation = self.r_allocation.add_qty(line, stop, qty, user)
            if line.item_id.type_item_id.uses_stock:
                # Materiales: se cargan desde el stock de la empresa (compras de Odoo)
                S_stock().take(line.order_id.company_id_id, line.item_id, qty, user, allocation=allocation,
                               description=f"Viaje {trip.code} · pedido {line.order_id.code}")
            stop.qty += qty
            stop.weight_kg += qty * (line.item_id.weight_kg or 0)
            self.r_line.save_stop(stop, user)

        S_order_line().refresh(requested.keys(), user)
        self.events.register(trip, user, "Pedidos agregados", event_type="comment",
                             description=", ".join(sorted({line.order_id.code for line in order_lines})))

    def _check_single_brand(self, trip, user, new_items):
        """Regla: cada viaje de motos lleva una sola marca."""
        items = list(new_items) + self.r_allocation.items_of_trip(trip)
        brands = {item.brand_id_id for item in items if item.is_vehicle}
        if not brands:
            return
        if None in brands:
            raise BusinessError("Las motos del viaje deben tener la marca registrada.", code="missing_brand")
        if len(brands) > 1 or (trip.brand_id_id and trip.brand_id_id not in brands):
            raise BusinessError("Un viaje de motos lleva una sola marca.", code="mixed_brand")
        trip.brand_id_id = brands.pop()
        self.repository.save_trip(trip, user, update_fields=["brand_id"])

    @transaction.atomic
    def assign(self, user, trip_id, *, vehicle_id, driver_id, carrier_id=None):
        """Asigna vehículo y conductor: disponibilidad, licencia, documentos y capacidad."""
        from apps.drivers.services import S_driver
        from apps.fleet.services import S_vehicle

        require_perm(user, "trips.assign_trip", "Solo el equipo de despacho asigna vehículo y conductor.")
        trip = self.lock(trip_id)
        self.require_state(trip, EDITABLE_STATES, "asignar vehículo y conductor")
        if not self.repository.has_stops(trip):
            raise BusinessError("El viaje no tiene paradas.")

        s_vehicle, s_driver = S_vehicle(), S_driver()
        vehicle = s_vehicle.get_for_trip(vehicle_id)
        driver = s_driver.get_for_trip(driver_id)
        other = self.repository.busy_trip_for(trip, vehicle=vehicle)
        if other:
            raise BusinessError(f"El vehículo {vehicle.plate} está en el viaje {other.code}.", code="vehicle_busy")
        other = self.repository.busy_trip_for(trip, driver=driver)
        if other:
            raise BusinessError(f"El conductor {driver} está en el viaje {other.code}.", code="driver_busy")
        today = timezone.localdate()
        s_driver.check_can_drive(driver, vehicle, today)
        s_vehicle.check_documents(vehicle, today)
        s_vehicle.check_capacity(vehicle, self.repository.total_weight(trip),
                                 self.r_allocation.motorcycles_of_trip(trip))

        carrier = vehicle.company_id
        if carrier_id is not None:
            carrier = R_company().get_active(carrier_id)
            if carrier is None:
                raise BusinessNotFound("El transportador no existe.")
        trip.vehicle_id, trip.driver_id, trip.carrier_id = vehicle, driver, carrier
        self.set_state(trip, user, "assigned", "Vehículo y conductor asignados", description=f"{vehicle.plate} / {driver}")
        return trip

    @transaction.atomic
    def cancel(self, user, trip_id, reason):
        """Cancela un viaje que no ha salido y devuelve las cantidades a los pedidos."""
        require_perm(user, "trips.cancel_trip", "Solo el equipo de despacho cancela viajes.")
        trip = self.lock(trip_id)
        self.require_state(trip, EDITABLE_STATES, "cancelar (ya salió a ruta)")
        if not (reason or "").strip():
            raise BusinessError("Indica el motivo de la cancelación.")
        self.set_state(trip, user, "cancelled", "Viaje cancelado", description=reason)
        s_stock = S_stock()
        for allocation in self.r_allocation.of_trip(trip).select_related(
                "order_line_id__item_id__type_item_id", "order_line_id__order_id"):
            s_stock.give_back_allocation(allocation, "trip_cancel_in", user, description=f"Viaje {trip.code} cancelado")
        S_order_line().refresh(self.r_allocation.order_line_ids_of_trip(trip), user)
        return trip

    # ------------------------------------------------------------------
    # 4. Salida
    # ------------------------------------------------------------------
    @transaction.atomic
    def depart(self, user, trip_id, *, latitude=None, longitude=None):
        trip = self.lock(trip_id)
        self.require_driver(trip, user)
        self.require_state(trip, ("assigned",), "salir a ruta")
        r_serie = R_trip_line_serie()
        for allocation in self.r_allocation.serialized_of_trip(trip):
            registered = r_serie.registered_count(allocation)
            if registered != allocation.qty:
                raise BusinessError(
                    f"Parada {allocation.trip_line_id.sequence}: faltan {allocation.qty - registered:.0f} VIN de "
                    f"{allocation.order_line_id.item_id} por registrar.", code="missing_series",
                )
        from apps.trips.services.S_document import require_loading_documents

        require_loading_documents(trip)
        trip.departure_date = timezone.now()
        self.r_line.start_route(trip)
        self.set_state(trip, user, "in_route", "Salida a ruta", latitude=latitude, longitude=longitude)
        return trip

    # ------------------------------------------------------------------
    # 8. Cierre y devolución
    # ------------------------------------------------------------------
    def close_if_done(self, trip, user):
        """Cierra el viaje cuando todas las paradas quedaron entregadas o devueltas."""
        from apps.drivers.services import S_driver

        if not self.repository.all_stops_finished(trip):
            return
        trip.closed_date = timezone.now()
        self.set_state(trip, user, "closed", "Viaje cerrado")
        if trip.driver_id_id:
            S_driver().refresh_rating(trip.driver_id_id)

    @transaction.atomic
    def create_return_trip(self, user, trip_id, trip_line_id, *, origin_address_id=None):
        """Despacho genera el viaje de regreso de una parada devuelta (vuelve a la bodega de origen)."""
        require_perm(user, "trips.create_return_trip", "Solo el equipo de despacho genera viajes de regreso.")
        trip = self.lock(trip_id)
        stop = self.r_line.get_for_update(trip, trip_line_id)
        if stop is None:
            raise BusinessNotFound("La parada no pertenece a este viaje.")
        if stop.state != "returned":
            raise BusinessError("Solo se genera viaje de regreso para una parada devuelta.")
        existing = self.repository.active_return_trip_for(stop)
        if existing:
            raise BusinessError(f"Ya existe el viaje de regreso {existing.code} para esta parada.")

        r_address = R_address()
        origin = stop.address_id
        if origin_address_id is not None:
            origin = r_address.get_active(origin_address_id)
            if origin is None:
                raise BusinessNotFound("La dirección de origen no existe.")
        warehouse = trip.origin_address_id

        return_trip = self.repository.create_trip(
            company_id_id=trip.company_id_id, trip_type="return", brand_id_id=trip.brand_id_id,
            origin_address_id=origin, parent_trip_id=trip, returned_line_id=stop,
            notes=f"Devolución de {trip.code}, parada {stop.sequence}: {stop.return_reason}", create_user=user,
        )
        return_stop = self.r_line.create_stop(trip_id=return_trip, sequence=1, recipient_id_id=warehouse.company_id_id,
                                              address_id=warehouse, qty=stop.qty, weight_kg=stop.weight_kg,
                                              create_user=user)
        r_serie = R_trip_line_serie()
        for serie in r_serie.of_stop(stop):
            r_serie.create_serie(trip_line_id=return_stop, vin=serie.vin, engine_number=serie.engine_number,
                                 create_user=user)
        self.events.register(return_trip, user, "Viaje de regreso armado", to_state="draft",
                             description=f"Desde {trip.code}, parada {stop.sequence}")
        self.events.register(trip, user, f"Viaje de regreso {return_trip.code} creado", event_type="comment", line=stop)
        return return_trip

    # ------------------------------------------------------------------
    # Lectura
    # ------------------------------------------------------------------
    def scope(self, user) -> dict | None:
        """Despacho ve todo; el conductor, sus viajes; el comercial, los de sus empresas."""
        from apps.drivers.services import S_driver

        if has_perm(user, "trips.view_all_trip"):
            return None
        if S_driver().get_by_user(user) is not None:
            return {"driver_id__user_id": user.id}
        return {"company_id__in": user_company_ids(user)}

    def detail(self, user, trip_id):
        require_perm(user, "trips.view_m_trip", "No tienes permiso para ver viajes.")
        trip = self.repository.with_detail(self.repository.visible(self.scope(user))).filter(pk=trip_id).first()
        if trip is None:
            raise BusinessNotFound("El viaje no existe.")
        return trip

    def list_scoped(self, user, data: dict):
        """Como ``list.relations`` del motor, limitado a lo que el usuario puede ver."""
        data = dict(data or {})
        scope = self.scope(user)
        if scope:
            data["filters"] = {**(data.get("filters") or {}), **scope}
        data.pop("user", None)
        return self.list_with_relations_m2m(user=user, **data)

    def resources(self, user):
        """Vehículos y conductores activos (la asignación valida documentos y disponibilidad)."""
        from apps.drivers.models import M_driver
        from apps.fleet.models import M_vehicle

        require_perm(user, "trips.assign_trip", "Solo el equipo de despacho asigna viajes.")
        vehicles = M_vehicle.objects.filter(is_active=True).select_related("type_vehicle_id").order_by("plate")
        drivers = M_driver.objects.filter(is_active=True).select_related("user_id").order_by("user_id__first_name")
        return {
            "vehicles": [{"id": v.id, "name": f"{v.plate} · {v.type_vehicle_id.name}", "is_available": v.is_available}
                         for v in vehicles],
            "drivers": [{"id": d.id, "name": str(d), "is_available": d.is_available} for d in drivers],
        }

    def mine(self, user):
        require_perm(user, "trips.drive_trip", "Solo los conductores tienen viajes asignados.")
        return list(self.repository.active_for_driver_user(user))
