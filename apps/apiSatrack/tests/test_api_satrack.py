"""Integración con Satrack contra un servidor simulado (sin red)."""

import re
from datetime import timedelta
from decimal import Decimal
from unittest import mock

from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.fleet.models import M_vehicle, M_vehicle_gps
from apps.testing import build_world, run_workflow
from apps.trips.models import M_trip, M_trip_line

SATRACK = {
    "SATRACK_ENABLED": True,
    "SATRACK_AUTH_URL": "https://auth.satrack.test",
    "SATRACK_LOCATION_URL": "https://satrack.test/api",
    "SATRACK_CLIENT_ID": "hurgo",
    "SATRACK_CLIENT_SECRET": "",
    "SATRACK_USERNAME": "api",
    "SATRACK_PASSWORD": "clave",
}
POST = "apps.apiSatrack.repository.apiSatrack.requests.post"


def event(plate, lat, lng, epoch=1, **extra):
    return {"serviceCode": plate, "latitude": lat, "longitude": lng, "speed": 42, "direction": "Norte",
            "address": "Cl 1", "town": "Valledupar", "unifiedEventCode": "01", "description": "Reporte",
            "generationDate": "2026-11-20T10:00:00", "generationDateEpochGMT": epoch, "id": f"e{epoch}", **extra}


def response(status, body=None):
    r = mock.Mock(status_code=status)
    r.json.return_value = body if body is not None else {}
    return r


class FakeSatrack:
    """Responde como Keycloak (token) y la API GraphQL de localización (last / byDate)."""

    def __init__(self, last=None, history=None):
        self.last = last or {}  # placa -> último evento (placas de la cuenta)
        self.history = history or {}  # placa -> eventos
        self.calls = []
        self.tokens = 0
        self.reject_once = set()

    def __call__(self, url, timeout=None, files=None, json=None, headers=None):
        if url == "https://auth.satrack.test/api/v1/Keycloak/authenticate":
            form = {name: value[1] for name, value in files.items()}
            self.calls.append(("auth", form))
            if form.get("Password") == "mala":  # así responde Satrack: 200 sin token
                return response(200, {"access_token": None, "expires_in": 0, "token_type": None})
            self.tokens += 1
            return response(200, {"access_token": f"tok-{self.tokens}", "expires_in": 300, "token_type": "Bearer"})
        assert url == "https://satrack.test/api/location", url
        token = headers["Authorization"].removeprefix("Bearer ")
        if token in self.reject_once:
            self.reject_once.discard(token)
            return response(401)
        query = json["query"]
        if "last(" in query:
            plates = re.findall(r'"([A-Z0-9]+)"', query.split("serviceCodes:")[1].split("]")[0])
            self.calls.append(("last", plates, token))
            if any(p not in self.last for p in plates):
                return response(400)
            return response(200, {"data": {"last": [self.last[p] for p in plates]}})
        match = re.search(r'serviceCode: "(\w+)", currentPage: (\d+), itemsPerPage: (\d+), '
                          r'initialDate: "([^"]+)", endDate: "([^"]+)"', query)
        plate, page, size = match.group(1), int(match.group(2)), int(match.group(3))
        self.calls.append(("byDate", plate, page, match.group(4), match.group(5)))
        events = self.history.get(plate, [])[(page - 1) * size:page * size]
        return response(200, {"data": {"byDate": {"pagination": {"currentPage": page}, "events": events}}})

    def of(self, kind):
        return [c for c in self.calls if c[0] == kind]


@override_settings(**SATRACK)
class ApiSatrackTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        build_world(cls)
        base = {"company_id": cls.hurgo, "brand_vehicle_id": cls.vehicle.brand_vehicle_id,
                "type_vehicle_id": cls.vehicle.type_vehicle_id, "owner_id": cls.vehicle.owner_id}
        cls.own_gps = M_vehicle.objects.create(plate="XYZ789", **base)  # cuenta Satrack propia
        M_vehicle_gps.objects.create(vehicle_id=cls.own_gps, operator="Satrack", username="otro", password="clave2",
                                     api_key="cliente2")
        cls.other_gps = M_vehicle.objects.create(plate="GPS001", **base)  # otro operador GPS
        M_vehicle_gps.objects.create(vehicle_id=cls.other_gps, operator="Otro GPS", username="x", password="y")

        for address, (lat, lng) in ((cls.warehouse, ("10.463400", "-73.253200")),
                                    (cls.dealer_addr, ("10.477000", "-73.250000"))):
            address.latitude, address.longitude = Decimal(lat), Decimal(lng)
            address.save()
        cls.trip = M_trip.objects.create(company_id=cls.uma, carrier_id=cls.hurgo, vehicle_id=cls.vehicle,
                                         driver_id=cls.driver, origin_address_id=cls.warehouse, state="in_route",
                                         departure_date=timezone.now() - timedelta(hours=1))
        cls.stop1 = M_trip_line.objects.create(trip_id=cls.trip, sequence=1, recipient_id=cls.dealer,
                                               address_id=cls.dealer_addr, state="in_route")
        cls.stop2 = M_trip_line.objects.create(trip_id=cls.trip, sequence=2, recipient_id=cls.dealer2,
                                               address_id=cls.dealer2_addr)  # sin coordenadas

    def setUp(self):
        cache.clear()

    def fake(self, **kwargs):
        kwargs.setdefault("last", {"ABC123": event("ABC123", 10.47, -73.25), "XYZ789": event("XYZ789", 4.6, -74.08)})
        return FakeSatrack(**kwargs)

    def ok(self, result):
        self.assertTrue(result.ok, result.reason)
        return result.data

    # ------------------------------------------------------------------
    # Posiciones
    # ------------------------------------------------------------------
    def test_positions_lnglat_and_token_cache(self):
        fake = self.fake()
        with mock.patch(POST, side_effect=fake):
            data = self.ok(run_workflow(self.dispatch, "apiSatrack.positions", {"plates": ["abc-123"]}))
            cache.delete("satrack_pos_ABC123")
            self.ok(run_workflow(self.dispatch, "apiSatrack.positions", {"plates": ["ABC123"]}))
        (marker,) = data["vehicles"]
        self.assertTrue(marker["found"])
        self.assertEqual(marker["coordinates"], [-73.25, 10.47])  # [lng, lat] como mapcn
        self.assertEqual((marker["longitude"], marker["latitude"], marker["speed"]), (-73.25, 10.47, 42))
        auth = fake.of("auth")
        self.assertEqual(len(auth), 1)  # el token queda en caché
        self.assertEqual(auth[0][1], {"Client_id": "hurgo", "Grant_type": "password", "Username": "api",
                                      "Password": "clave"})
        self.assertEqual(len(fake.of("last")), 2)

    def test_positions_cache_avoids_calls(self):
        fake = self.fake()
        with mock.patch(POST, side_effect=fake):
            self.ok(run_workflow(self.dispatch, "apiSatrack.positions", {"plates": ["ABC123"]}))
            self.ok(run_workflow(self.dispatch, "apiSatrack.positions", {"plates": ["ABC123"]}))
        self.assertEqual(len(fake.of("last")), 1)

    def test_positions_per_vehicle_account_and_other_operator(self):
        fake = self.fake()
        with mock.patch(POST, side_effect=fake):
            data = self.ok(run_workflow(self.dispatch, "apiSatrack.positions"))
        markers = {m["plate"]: m for m in data["vehicles"]}
        self.assertEqual(set(markers), {"ABC123", "XYZ789", "GPS001"})
        self.assertTrue(markers["ABC123"]["found"] and markers["XYZ789"]["found"])
        self.assertFalse(markers["GPS001"]["found"])
        self.assertFalse(markers["GPS001"]["satrack"])
        self.assertEqual({c[1]["Client_id"] for c in fake.of("auth")}, {"hurgo", "cliente2"})
        queried = [p for c in fake.of("last") for p in c[1]]
        self.assertNotIn("GPS001", queried)

    def test_unknown_plate_falls_back_one_by_one(self):
        fake = self.fake(last={"ABC123": event("ABC123", 10.47, -73.25)})
        base = {"company_id": self.hurgo, "brand_vehicle_id": self.vehicle.brand_vehicle_id,
                "type_vehicle_id": self.vehicle.type_vehicle_id, "owner_id": self.vehicle.owner_id}
        M_vehicle.objects.create(plate="DEF456", **base)  # usa la cuenta global pero no está en Satrack
        with mock.patch(POST, side_effect=fake):
            data = self.ok(run_workflow(self.dispatch, "apiSatrack.positions", {"plates": ["ABC123", "DEF456"]}))
            self.ok(run_workflow(self.dispatch, "apiSatrack.positions", {"plates": ["DEF456"]}))
        found = {m["plate"]: m["found"] for m in data["vehicles"]}
        self.assertEqual(found, {"ABC123": True, "DEF456": False})
        self.assertEqual([c[1] for c in fake.of("last")], [["ABC123", "DEF456"], ["ABC123"], ["DEF456"]])

    def test_expired_token_reauthenticates_once(self):
        fake = self.fake()
        fake.reject_once.add("tok-1")
        with mock.patch(POST, side_effect=fake):
            data = self.ok(run_workflow(self.dispatch, "apiSatrack.positions", {"plates": ["ABC123"]}))
        self.assertTrue(data["vehicles"][0]["found"])
        self.assertEqual(len(fake.of("auth")), 2)

    @override_settings(SATRACK_PASSWORD="mala")
    def test_bad_credentials_are_reported(self):
        with mock.patch(POST, side_effect=self.fake()):
            data = self.ok(run_workflow(self.dispatch, "apiSatrack.positions", {"plates": ["ABC123"]}))
        self.assertFalse(data["vehicles"][0]["found"])
        self.assertIn("rechazó las credenciales", data["satrack"]["errors"][0])

    @override_settings(SATRACK_ENABLED=False)
    def test_disabled(self):
        with mock.patch(POST) as post:
            result = run_workflow(self.dispatch, "apiSatrack.positions")
            data = self.ok(run_workflow(self.dispatch, "apiSatrack.map_overview"))
        self.assertFalse(result.ok)
        self.assertIn("SATRACK_ENABLED", result.reason)
        post.assert_not_called()
        self.assertFalse(data["satrack"]["enabled"])
        self.assertEqual(len(data["arcs"]), 1)  # el mapa sigue con origen y paradas
        self.assertFalse(data["vehicles"][0]["found"])

    def test_positions_require_fleet_permission(self):
        with mock.patch(POST, side_effect=self.fake()):
            self.assertFalse(run_workflow(self.driver_user, "apiSatrack.positions").ok)
            self.assertFalse(run_workflow(self.commercial, "apiSatrack.history", {"plate": "ABC123"}).ok)

    # ------------------------------------------------------------------
    # Historial
    # ------------------------------------------------------------------
    def test_history_paginates_sorts_and_clamps_to_5_days(self):
        events = [event("ABC123", 10 + i / 1000, -73 - i / 1000, epoch=1000 - i) for i in range(150)]
        fake = self.fake(history={"ABC123": events})
        start = (timezone.now() - timedelta(days=10)).isoformat()
        with mock.patch(POST, side_effect=fake):
            data = self.ok(run_workflow(self.dispatch, "apiSatrack.history",
                                        {"vehicle_id": self.vehicle.id, "start": start}))
        self.assertTrue(data["clamped"])
        self.assertFalse(data["truncated"])
        self.assertEqual(len(data["coordinates"]), 150)
        self.assertEqual(data["coordinates"][0], [-73.149, 10.149])  # el más antiguo primero
        calls = fake.of("byDate")
        self.assertEqual([c[2] for c in calls], [1, 2])
        self.assertRegex(calls[0][3], r"^\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}$")

    def test_history_vehicle_without_satrack(self):
        with mock.patch(POST, side_effect=self.fake()):
            result = run_workflow(self.dispatch, "apiSatrack.history", {"plate": "GPS001"})
        self.assertFalse(result.ok)
        self.assertIn("no tiene GPS Satrack", result.reason)

    # ------------------------------------------------------------------
    # Mapa (mapcn)
    # ------------------------------------------------------------------
    def test_map_overview_arcs_stops_and_vehicle(self):
        with mock.patch(POST, side_effect=self.fake()):
            data = self.ok(run_workflow(self.dispatch, "apiSatrack.map_overview"))
        (arc,) = data["arcs"]
        self.assertEqual(arc["from"], [-73.2532, 10.4634])
        self.assertEqual(arc["to"], [-73.25, 10.477])
        self.assertEqual(arc["trip_code"], self.trip.code)
        self.assertEqual(arc["destination"], "Concesionario 1 · Sede 1")
        self.assertEqual([s["trip_line_id"] for s in data["stops"]], [self.stop1.id])
        self.assertEqual(data["missing_coordinates"][0]["trip_line_id"], self.stop2.id)
        (vehicle,) = data["vehicles"]
        self.assertEqual((vehicle["plate"], vehicle["found"], vehicle["coordinates"]), ("ABC123", True, [-73.25, 10.47]))
        self.assertEqual(data["trips"][0]["state"], "in_route")

    def test_map_overview_hub_mode(self):
        self.dealer2_addr.latitude, self.dealer2_addr.longitude = Decimal("10.5"), Decimal("-73.3")
        self.dealer2_addr.save()
        with mock.patch(POST, side_effect=self.fake()):
            legs = self.ok(run_workflow(self.dispatch, "apiSatrack.map_overview"))["arcs"]
            hub = self.ok(run_workflow(self.dispatch, "apiSatrack.map_overview", {"arc_mode": "hub"}))["arcs"]
        self.assertEqual(legs[1]["from"], legs[0]["to"])  # parada 1 -> parada 2
        self.assertEqual(hub[1]["from"], hub[0]["from"])  # origen -> cada parada

    def test_map_overview_visibility(self):
        with mock.patch(POST, side_effect=self.fake()):
            mine = self.ok(run_workflow(self.commercial, "apiSatrack.map_overview"))
            other = self.ok(run_workflow(self.other_commercial, "apiSatrack.map_overview"))
            driver = self.ok(run_workflow(self.driver_user, "apiSatrack.map_overview"))
            driver2 = self.ok(run_workflow(self.driver2_user, "apiSatrack.map_overview"))
        self.assertEqual(len(mine["trips"]), 1)
        self.assertEqual(len(driver["trips"]), 1)
        self.assertEqual(other["trips"], [])
        self.assertEqual(driver2["trips"], [])

    def test_trip_map_with_route(self):
        events = [event("ABC123", 10.46 + i / 100, -73.25, epoch=i) for i in range(3)]
        with mock.patch(POST, side_effect=self.fake(history={"ABC123": events})):
            data = self.ok(run_workflow(self.commercial, "apiSatrack.trip_map", {"trip_id": self.trip.id}))
            hidden = run_workflow(self.other_commercial, "apiSatrack.trip_map", {"trip_id": self.trip.id})
        self.assertEqual(data["trip"]["code"], self.trip.code)
        self.assertTrue(data["vehicle"]["found"])
        self.assertEqual(data["route"]["coordinates"], [[-73.25, 10.46], [-73.25, 10.47], [-73.25, 10.48]])
        self.assertEqual(len(data["arcs"]), 1)
        self.assertFalse(hidden.ok)
