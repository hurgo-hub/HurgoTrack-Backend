"""Pasos 1 (pedido) y 2 (confirmación) por los workflows del motor, y su enlace con viajes."""

import shutil
import tempfile

from django.test import override_settings
from rest_framework.test import APITestCase

from apps.testing import build_world, proof_file, run_workflow
from apps.orders.models import M_order, M_order_line

MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class OrderFlowTests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)

    @classmethod
    def setUpTestData(cls):
        build_world(cls)

    def line(self, item, qty, address=None):
        return {"item_id": item.id, "qty": str(qty), "address_id": (address or self.dealer_addr).id}

    def payload(self, **overrides):
        data = {"address_id": self.warehouse.id, "notes": "Entregar en la mañana",
                "lines": [self.line(self.moto, 3), self.line(self.cement, "20.5")]}
        data.update(overrides)
        return data

    def create(self, user=None, **overrides):
        return run_workflow(user or self.commercial, "orders.create", self.payload(**overrides))

    def confirm(self, order_id, odoo="PO-001", user=None):
        return run_workflow(user or self.dispatch, "orders.confirm", {"order_id": order_id, "odoo_purchase": odoo})

    def ok(self, result):
        self.assertTrue(result.ok, result.reason)
        return result.data

    # ------------------------------------------------------------------
    def test_commercial_creates_order_for_own_company(self):
        order = self.ok(self.create())
        self.assertTrue(order["code"].startswith("P-"))
        self.assertEqual(order["state"], "requested")
        self.assertEqual(order["company"]["id"], self.uma.id)  # la única empresa del comercial
        self.assertEqual(order["address"]["id"], self.warehouse.id)
        self.assertEqual(len(order["lines"]), 2)
        self.assertEqual(order["created_by"]["id"], self.commercial.id)
        self.assertEqual([e["name"] for e in order["events"]], ["Pedido creado", "Pedido enviado a Hurgo"])

    def test_lines_can_go_to_different_addresses(self):
        """Cada línea va a una dirección de entrega de la empresa que pide (una parada por dirección)."""
        order = self.ok(self.create(lines=[self.line(self.moto, 1), self.line(self.moto, 2, self.dealer2_addr)]))
        self.ok(self.confirm(order["id"]))
        trip = self.ok(run_workflow(self.dispatch, "trips.build", {
            "company_id": self.uma.id, "origin_address_id": self.warehouse.id,
            "allocations": [{"order_line_id": line["id"], "qty": line["qty"]} for line in order["lines"]],
        }))
        self.assertEqual(sorted(stop["address"]["id"] for stop in trip["lines"]),
                         sorted([self.dealer_addr.id, self.dealer2_addr.id]))

    def test_who_can_create(self):
        self.assertIn("No puedes crear pedidos para esa empresa", self.create(company_id=self.akt.id).reason)
        self.assertIn("Permisos faltantes", self.create(user=self.driver_user).reason)
        self.assertIn("Indica la empresa", self.create(user=self.dispatch).reason)
        self.ok(self.create(user=self.dispatch, company_id=self.uma.id))
        self.assertIn("no está registrada como empresa cliente",
                      self.create(user=self.dispatch, company_id=self.hurgo.id).reason)

    def test_line_and_address_validations(self):
        cases = {
            "es de otra empresa": self.payload(lines=[self.line(self.akt_item, 1)]),
            "repetido": self.payload(lines=[self.line(self.moto, 1), self.line(self.moto, 2)]),
            "unidades enteras": self.payload(lines=[self.line(self.moto, "1.5")]),
            "no es de UMA": self.payload(lines=[self.line(self.moto, 1, address=self.akt_addr)]),
            "dirección de cargue no pertenece": self.payload(address_id=self.akt_addr.id),
            "lines": self.payload(lines=[]),
        }
        for expected, data in cases.items():
            result = run_workflow(self.commercial, "orders.create", data)
            self.assertFalse(result.ok, expected)
            self.assertIn(expected, result.reason)
        self.assertEqual(M_order.objects.filter(company_id=self.uma).count(), 3)  # solo los del escenario

    def test_draft_submit_and_edit_until_confirmed(self):
        order = self.ok(self.create(submit=False))
        self.assertEqual(order["state"], "draft")
        self.assertIn("está 'Borrador'", self.confirm(order["id"]).reason)

        order = self.ok(run_workflow(self.commercial, "orders.update", {
            "order_id": order["id"], **self.payload(lines=[self.line(self.moto, 5, self.dealer2_addr)]),
        }))
        self.assertEqual((order["lines"][0]["address"]["id"], order["lines"][0]["qty"]), (self.dealer2_addr.id, "5.00"))
        self.assertEqual(self.ok(run_workflow(self.commercial, "orders.submit", {"order_id": order["id"]}))["state"],
                         "requested")
        order = self.ok(self.confirm(order["id"], odoo="  PO-778 "))
        self.assertEqual((order["state"], order["odoo_purchase"]), ("confirmed", "PO-778"))
        self.assertIsNotNone(order["confirmed_date"])
        result = run_workflow(self.commercial, "orders.update", {"order_id": order["id"], **self.payload()})
        self.assertIn("está 'Confirmado'", result.reason)

    def test_only_dispatch_confirms_and_odoo_is_required(self):
        order = self.ok(self.create())
        self.assertIn("Permisos faltantes", self.confirm(order["id"], user=self.commercial).reason)
        for odoo in ("", "   "):  # sin stock (motos): la compra de Odoo sigue siendo obligatoria
            self.assertIn("referencia de la compra en Odoo", self.confirm(order["id"], odoo=odoo).reason)
        self.assertEqual(M_order.objects.get(pk=order["id"]).state, "requested")

    def test_cancel_rules(self):
        order = self.ok(self.create())
        order = self.ok(run_workflow(self.commercial, "orders.cancel", {"order_id": order["id"], "reason": "Desiste"}))
        self.assertEqual(order["state"], "cancelled")
        self.assertTrue(all(line["state"] == "cancelled" for line in order["lines"]))

        payload = {"order_id": self.order1.id, "reason": "Sin stock"}
        self.assertIn("solo lo cancela el equipo de despacho", run_workflow(self.commercial, "orders.cancel", payload).reason)
        trip = self.ok(run_workflow(self.dispatch, "trips.build", {
            "company_id": self.uma.id, "origin_address_id": self.warehouse.id,
            "allocations": [{"order_line_id": self.l_cement.id, "qty": "4"}],
        }))
        self.assertIn("tiene cantidades en viajes", run_workflow(self.dispatch, "orders.cancel", payload).reason)
        self.ok(run_workflow(self.dispatch, "trips.cancel", {"trip_id": trip["id"], "reason": "x"}))
        self.assertEqual(self.ok(run_workflow(self.dispatch, "orders.cancel", payload))["state"], "cancelled")

    def test_visibility(self):
        order = self.ok(self.create())
        self.assertIn("no existe", run_workflow(self.other_commercial, "orders.retrieve", {"order_id": order["id"]}).reason)
        listing = {"data": {"fields": ["id", "code", "state"], "limit": 50}}
        self.assertEqual(self.ok(run_workflow(self.other_commercial, "orders.list", listing)), [])
        self.assertEqual(len(self.ok(run_workflow(self.commercial, "orders.list", listing))), 4)
        self.assertEqual(len(self.ok(run_workflow(self.dispatch, "orders.list", listing))), 4)
        self.assertIn("Permisos faltantes", run_workflow(self.driver_user, "orders.list", listing).reason)

    def test_lookups(self):
        items = self.ok(run_workflow(self.commercial, "orders.items"))
        self.assertEqual({i["name"] for i in items}, {"UMA 125", "Otra 150", "Cemento"})
        # Las direcciones de entrega son las de su propia empresa
        addresses = self.ok(run_workflow(self.commercial, "locations.addresses"))
        self.assertEqual({a["id"] for a in addresses}, {self.warehouse.id, self.dealer_addr.id, self.dealer2_addr.id})
        self.assertFalse(run_workflow(self.commercial, "locations.addresses", {"company_id": self.akt.id}).ok)
        self.assertIn("Permisos faltantes", run_workflow(self.driver_user, "locations.addresses").reason)

    def test_end_to_end_tracking(self):
        """Pedido -> confirmación -> viaje -> entrega: el cliente ve todo en el historial del pedido."""
        order = self.ok(self.create(lines=[self.line(self.cement, 10)]))
        self.ok(self.confirm(order["id"]))
        line_id = M_order_line.objects.get(order_id=order["id"]).id
        trip = self.ok(run_workflow(self.dispatch, "trips.build", {
            "company_id": self.uma.id, "origin_address_id": self.warehouse.id,
            "allocations": [{"order_line_id": line_id, "qty": "10"}],
        }))
        self.ok(run_workflow(self.dispatch, "trips.assign",
                             {"trip_id": trip["id"], "vehicle_id": self.vehicle.id, "driver_id": self.driver.id}))
        self.ok(run_workflow(self.driver_user, "trips.depart", {"trip_id": trip["id"]}))

        tracking = self.ok(run_workflow(self.commercial, "orders.retrieve", {"order_id": order["id"]}))
        self.assertEqual(tracking["state"], "in_progress")
        self.assertEqual((tracking["lines"][0]["trips"][0]["trip_code"], tracking["lines"][0]["trips"][0]["stop_state"]),
                         (trip["code"], "in_route"))

        self.ok(run_workflow(self.driver_user, "trips.deliver",
                             {"trip_id": trip["id"], "trip_line_id": trip["lines"][0]["id"]}, files=[proof_file()]))
        tracking = self.ok(run_workflow(self.commercial, "orders.retrieve", {"order_id": order["id"]}))
        self.assertEqual((tracking["state"], tracking["lines"][0]["qty_delivered"]), ("delivered", "10.00"))
        self.assertEqual([e["name"] for e in tracking["events"]],
                         ["Pedido creado", "Pedido enviado a Hurgo", "Compra confirmada en Odoo", "Pedido en despacho",
                          "Pedido entregado"])
        responsible = {e["name"]: e["user"]["id"] for e in tracking["events"]}
        self.assertEqual((responsible["Compra confirmada en Odoo"], responsible["Pedido entregado"]),
                         (self.dispatch.id, self.driver_user.id))
