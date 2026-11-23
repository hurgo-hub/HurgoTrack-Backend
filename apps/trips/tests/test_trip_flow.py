"""Flujo de viajes de punta a punta (pasos 3 a 8) por los workflows del motor."""

import shutil
import tempfile
from datetime import date, timedelta
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APIClient, APITestCase

from apps.core.testing import PASSWORD, build_world, proof_file, run_workflow
from apps.fleet.models import M_soat
from apps.trips.models import M_trip, M_trip_attach, M_trip_line

MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class TripFlowTests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)

    @classmethod
    def setUpTestData(cls):
        build_world(cls)

    # ------------------------------------------------------------------
    def build_trip(self, allocations=None, user=None):
        allocations = allocations or [
            {"order_line_id": self.l_moto.id, "qty": "2"},
            {"order_line_id": self.l_cement.id, "qty": "10"},
            {"order_line_id": self.l_moto2.id, "qty": "1"},
        ]
        return run_workflow(user or self.dispatch, "trips.build", {
            "company_id": self.uma.id, "origin_address_id": self.warehouse.id, "allocations": allocations,
        })

    def ok(self, result):
        self.assertTrue(result.ok, result.reason)
        return result.data

    def stop(self, trip, recipient):
        return next(line for line in trip["lines"] if line["recipient"]["id"] == recipient.id)

    def register_vins(self, trip):
        n = 0
        for line in trip["lines"]:
            series = []
            for item in line["items"]:
                for _ in range(int(Decimal(item["qty"])) if item["is_serialized"] else 0):
                    n += 1
                    series.append({"order_line_trip_id": item["order_line_trip_id"], "vin": f"vin{trip['id']}x{n}"})
            if series:
                trip = self.ok(run_workflow(self.dispatch, "trips.register_series",
                                            {"trip_id": trip["id"], "trip_line_id": line["id"], "series": series}))
        return trip

    def assign(self, trip, driver=None):
        return run_workflow(self.dispatch, "trips.assign", {
            "trip_id": trip["id"], "vehicle_id": self.vehicle.id, "driver_id": (driver or self.driver).id,
        })

    def ready_to_go(self):
        trip = self.register_vins(self.ok(self.build_trip()))
        return self.ok(self.assign(trip))

    def deliver(self, trip, stop, user=None, files=None, **data):
        return run_workflow(user or self.driver_user, "trips.deliver",
                            {"trip_id": trip["id"], "trip_line_id": stop["id"], **data},
                            files=[proof_file()] if files is None else files)

    # ------------------------------------------------------------------
    def test_full_flow_closes_trip_and_delivers_orders(self):
        trip = self.ok(self.build_trip())
        self.assertEqual((trip["state"], trip["brand"], len(trip["lines"])), ("draft", "UMA", 2))
        self.assertEqual(Decimal(self.stop(trip, self.dealer)["weight_kg"]), Decimal("740"))  # 2*120 + 10*50
        self.l_moto.refresh_from_db()
        self.order1.refresh_from_db()
        self.assertEqual((self.l_moto.state, self.order1.state), ("assigned", "in_progress"))

        trip = self.register_vins(trip)
        trip = self.ok(self.assign(trip))
        self.assertEqual(trip["state"], "assigned")
        mine = self.ok(run_workflow(self.driver_user, "trips.mine"))
        self.assertEqual([t["code"] for t in mine], [trip["code"]])

        trip = self.ok(run_workflow(self.driver_user, "trips.depart",
                                    {"trip_id": trip["id"], "latitude": 10.4631234567, "longitude": -73.25}))
        self.assertEqual(trip["state"], "in_route")
        stop1, stop2 = self.stop(trip, self.dealer), self.stop(trip, self.dealer2)
        trip = self.ok(run_workflow(self.driver_user, "trips.start_delivery",
                                    {"trip_id": trip["id"], "trip_line_id": stop1["id"]}))
        self.assertEqual(trip["state"], "delivering")

        self.ok(self.deliver(trip, stop1, rating=5, comment="ok"))
        trip = self.ok(self.deliver(trip, stop2, rating=4))
        self.assertEqual(trip["state"], "closed")
        self.assertIsNotNone(trip["closed_date"])
        self.assertTrue(all(s["state"] == "delivered" for line in trip["lines"] for s in line["series"]))
        self.assertEqual(
            M_trip_attach.objects.filter(trip_id=trip["id"], type_attach_id__key="delivery_proof").count(), 2)
        for order in (self.order1, self.order2):
            order.refresh_from_db()
            self.assertEqual(order.state, "delivered")
        self.driver.refresh_from_db()
        self.assertEqual(self.driver.average_rating, Decimal("4.50"))
        names = [e["name"] for e in trip["events"]]
        self.assertIn("Salida a ruta", names)
        self.assertIn("Viaje cerrado", names)
        self.assertTrue(all(e["user"] for e in trip["events"]))

    def test_one_brand_per_motorcycle_trip(self):
        r = self.build_trip([{"order_line_id": self.l_moto.id, "qty": "2"},
                             {"order_line_id": self.l_other.id, "qty": "1"}])
        self.assertFalse(r.ok)
        self.assertIn("una sola marca", r.reason)
        self.assertFalse(M_trip.objects.exists())  # el workflow revierte todo

    def test_cannot_assign_more_than_pending(self):
        self.assertIn("solo quedan 2.00", self.build_trip([{"order_line_id": self.l_moto.id, "qty": "3"}]).reason)
        self.ok(self.build_trip([{"order_line_id": self.l_moto.id, "qty": "1"}]))
        self.assertIn("solo quedan 1.00", self.build_trip([{"order_line_id": self.l_moto.id, "qty": "2"}]).reason)
        self.l_moto.refresh_from_db()
        self.assertEqual(self.l_moto.state, "partial")

    def test_permissions_are_checked_by_workflow_and_service(self):
        self.assertIn("Permisos faltantes", self.build_trip(user=self.commercial).reason)
        self.assertIn("Permisos faltantes", self.build_trip(user=self.driver_user).reason)
        anonymous = run_workflow(None, "trips.build", {"company_id": self.uma.id})
        self.assertFalse(anonymous.ok)
        self.assertTrue(self.build_trip(user=self.admin).ok)

    def test_only_assigned_driver_confirms_delivery(self):
        trip = self.ready_to_go()
        self.ok(run_workflow(self.driver_user, "trips.depart", {"trip_id": trip["id"]}))
        stop = trip["lines"][0]
        # Despacho no tiene drive_trip: lo frena validate.permission en el workflow.
        self.assertIn("Permisos faltantes", self.deliver(trip, stop, user=self.dispatch).reason)
        # El superusuario pasa el workflow, pero el servicio exige ser el conductor asignado.
        self.assertIn("conductor asignado", self.deliver(trip, stop, user=self.superuser).reason)
        r = self.deliver(trip, stop, user=self.driver2_user)  # otro conductor
        self.assertIn("conductor asignado", r.reason)
        self.assertEqual(M_trip_line.objects.get(pk=stop["id"]).state, "in_route")

    def test_delivery_requires_signed_remission_photo(self):
        trip = self.ready_to_go()
        self.ok(run_workflow(self.driver_user, "trips.depart", {"trip_id": trip["id"]}))
        stop = trip["lines"][0]
        self.assertIn("remisión firmada", self.deliver(trip, stop, files=[]).reason)
        self.assertIn("x.exe", self.deliver(trip, stop, files=[SimpleUploadedFile("x.exe", b"MZ")]).reason)
        self.assertEqual(M_trip_line.objects.get(pk=stop["id"]).state, "in_route")

    def test_depart_requires_all_vins(self):
        trip = self.ok(self.build_trip())
        self.ok(self.assign(trip))
        r = run_workflow(self.driver_user, "trips.depart", {"trip_id": trip["id"]})
        self.assertIn("VIN", r.reason)

    def test_vin_cannot_travel_in_two_trips(self):
        trips = [self.ok(self.build_trip([{"order_line_id": self.l_moto.id, "qty": "1"}])) for _ in range(2)]
        results = []
        for trip in trips:
            item = trip["lines"][0]["items"][0]
            results.append(run_workflow(self.dispatch, "trips.register_series", {
                "trip_id": trip["id"], "trip_line_id": trip["lines"][0]["id"],
                "series": [{"order_line_trip_id": item["order_line_trip_id"], "vin": " abc 123 "}],
            }))
        self.assertTrue(results[0].ok, results[0].reason)
        self.assertIn(f"ya está en el viaje {trips[0]['code']}", results[1].reason)

    def test_assign_checks_documents_and_license(self):
        trip = self.register_vins(self.ok(self.build_trip()))
        self.assertIn("La licencia B1", self.assign(trip, driver=self.driver2).reason)
        M_soat.objects.update(date_expire=date.today() - timedelta(days=1))
        self.assertIn("SOAT vigente", self.assign(trip).reason)

    def test_return_releases_qty_and_creates_return_trip(self):
        trip = self.ready_to_go()
        self.ok(run_workflow(self.driver_user, "trips.depart", {"trip_id": trip["id"]}))
        stop1, stop2 = self.stop(trip, self.dealer), self.stop(trip, self.dealer2)
        self.ok(self.deliver(trip, stop1))
        trip = self.ok(run_workflow(self.driver_user, "trips.register_return",
                                    {"trip_id": trip["id"], "trip_line_id": stop2["id"], "reason": "No recibe"},
                                    files=[proof_file("dev.jpg")]))
        self.assertEqual(trip["state"], "closed")
        returned = self.stop(trip, self.dealer2)
        self.assertEqual((returned["state"], returned["is_return"]), ("returned", True))
        self.l_moto2.refresh_from_db()
        self.order2.refresh_from_db()
        self.assertEqual((self.l_moto2.qty_assigned, self.l_moto2.state), (Decimal("0"), "pending"))
        self.assertEqual(self.order2.state, "confirmed")

        payload = {"trip_id": trip["id"], "trip_line_id": stop2["id"]}
        self.assertFalse(run_workflow(self.driver_user, "trips.create_return_trip", payload).ok)
        back = self.ok(run_workflow(self.dispatch, "trips.create_return_trip", payload))
        self.assertEqual((back["trip_type"], back["parent_trip"]), ("return", trip["code"]))
        self.assertEqual(back["lines"][0]["address"]["id"], self.warehouse.id)
        self.assertEqual(len(back["lines"][0]["series"]), 1)
        self.assertIn("Ya existe", run_workflow(self.dispatch, "trips.create_return_trip", payload).reason)

        # La moto devuelta se puede volver a despachar.
        new = self.ok(self.build_trip([{"order_line_id": self.l_moto2.id, "qty": "1"}]))
        item = new["lines"][0]["items"][0]
        self.ok(run_workflow(self.dispatch, "trips.register_series", {
            "trip_id": new["id"], "trip_line_id": new["lines"][0]["id"],
            "series": [{"order_line_trip_id": item["order_line_trip_id"], "vin": returned["series"][0]["vin"]}],
        }))

    def test_cancel_releases_order_quantities(self):
        trip = self.ok(self.build_trip())
        trip = self.ok(run_workflow(self.dispatch, "trips.cancel", {"trip_id": trip["id"], "reason": "Aplaza"}))
        self.assertEqual(trip["state"], "cancelled")
        self.l_moto.refresh_from_db()
        self.order1.refresh_from_db()
        self.assertEqual((self.l_moto.qty_assigned, self.l_moto.state, self.order1.state),
                         (Decimal("0"), "pending", "confirmed"))

    def test_novelty_with_and_without_photo(self):
        trip = self.ready_to_go()
        self.ok(run_workflow(self.driver_user, "trips.report_novelty",
                             {"trip_id": trip["id"], "name": "Trancón"}))
        trip = self.ok(run_workflow(self.driver_user, "trips.report_novelty",
                                    {"trip_id": trip["id"], "name": "Vía cerrada", "description": "Derrumbe"},
                                    files=[proof_file("via.jpg")]))
        self.assertEqual(len([e for e in trip["events"] if e["event_type"] == "novelty"]), 2)
        self.assertEqual([a["type_key"] for a in trip["attachments"]], ["novelty"])
        self.assertIn("Permisos faltantes",
                      run_workflow(self.commercial, "trips.report_novelty", {"trip_id": trip["id"], "name": "x"}).reason)

    def test_visibility_by_company_and_driver(self):
        trip = self.ok(self.build_trip())
        self.assertTrue(run_workflow(self.commercial, "trips.retrieve", {"trip_id": trip["id"]}).ok)
        self.assertIn("no existe", run_workflow(self.other_commercial, "trips.retrieve", {"trip_id": trip["id"]}).reason)
        self.assertIn("no existe", run_workflow(self.driver_user, "trips.retrieve", {"trip_id": trip["id"]}).reason)
        listing = {"data": {"fields": ["id", "code", "state"], "limit": 50}}
        self.assertEqual(len(self.ok(run_workflow(self.commercial, "trips.list", listing))), 1)
        self.assertEqual(self.ok(run_workflow(self.other_commercial, "trips.list", listing)), [])
        self.assertEqual(len(self.ok(run_workflow(self.dispatch, "trips.list", listing))), 1)

    def test_pending_order_lines_for_dispatch(self):
        lines = self.ok(run_workflow(self.dispatch, "orders.pending_lines", {"company_id": self.uma.id}))
        self.assertEqual(len(lines), 4)
        self.assertIn("Permisos faltantes", run_workflow(self.commercial, "orders.pending_lines").reason)

    def test_login_with_cookies_only(self):
        """Web y app móvil: el login del motor deja la cookie access_token; no se acepta Bearer."""
        trip = self.ready_to_go()
        client = APIClient()
        r = client.post("/api/auth/token/", {"username": "conductor", "password": PASSWORD}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.cookies["access_token"]["httponly"])
        self.assertNotIn("access", r.data)  # el token no viaja en el cuerpo
        r = client.post("/api/workflows/sync/trips.mine/", {}, format="json")
        self.assertTrue(r.data["success"], r.data)
        self.assertEqual(r.data["details"]["context"]["results"][0]["code"], trip["code"])

        bearer = APIClient()
        bearer.credentials(HTTP_AUTHORIZATION=f"Bearer {client.cookies['access_token'].value}")
        r = bearer.post("/api/workflows/sync/trips.mine/", {}, format="json")
        self.assertFalse(r.data["success"], r.data)
