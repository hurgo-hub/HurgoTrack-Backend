"""Integración con Odoo con el servidor JSON-RPC simulado (sin red)."""

import shutil
import tempfile
from unittest import mock

from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APITestCase

from apps.apiOdoo.models import M_odoo_purchase, M_odoo_sync_log
from enginedj.base.models import M_company
from apps.testing import build_world, proof_file, run_workflow

MEDIA_ROOT = tempfile.mkdtemp()
ODOO = {"ODOO_ENABLED": True, "ODOO_URL": "https://odoo.test", "ODOO_DB": "hurgo", "ODOO_USERNAME": "api@hurgo.co",
        "ODOO_API_KEY": "secreto", "MEDIA_ROOT": MEDIA_ROOT}


class FakeOdoo:
    """Responde /jsonrpc como Odoo: authenticate, search_read y message_post."""

    def __init__(self, purchases=None, partners=None):
        self.purchases = purchases or []
        self.partners = partners or []
        self.calls = []

    def __call__(self, url, json=None, timeout=None):
        params = json["params"]
        self.calls.append((params["service"], params["args"]))
        if params["method"] == "authenticate":
            result = 7
        else:
            model, method, args, kwargs = params["args"][3:7]
            if method == "search_read" and model == "purchase.order":
                name = args[0][0][2]
                result = [p for p in self.purchases if p["name"] == name]
            elif method == "search_read" and model == "res.partner":
                result = self.partners
            elif method == "message_post":
                result = 991
            else:
                result = []
        response = mock.Mock(status_code=200)
        response.json.return_value = {"jsonrpc": "2.0", "id": json["id"], "result": result}
        response.raise_for_status.return_value = None
        return response


def purchase(name="P00012", state="purchase"):
    return {"id": 12, "name": name, "state": state, "partner_id": [5, "UMA S.A.S."],
            "date_order": "2026-11-19 10:00:00", "amount_total": 1500000.0, "order_line": [1, 2]}


@override_settings(**ODOO)
class ApiOdooTests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)

    @classmethod
    def setUpTestData(cls):
        build_world(cls)

    def setUp(self):
        cache.clear()

    def requested_order(self):
        result = run_workflow(self.commercial, "orders.create", {
            "address_id": self.warehouse.id,
            "lines": [{"item_id": self.cement.id, "qty": "10", "recipient_id": self.dealer.id,
                       "address_id": self.dealer_addr.id}],
        })
        self.assertTrue(result.ok, result.reason)
        return result.data

    def test_confirm_validates_purchase_in_odoo(self):
        fake = FakeOdoo([purchase(), purchase("P00013", state="draft")])
        with mock.patch("apps.apiOdoo.repository.apiOdoo.requests.post", side_effect=fake):
            order = self.requested_order()
            result = run_workflow(self.dispatch, "orders.confirm", {"order_id": order["id"], "odoo_purchase": "P00099"})
            self.assertIn("no existe en Odoo", result.reason)
            result = run_workflow(self.dispatch, "orders.confirm", {"order_id": order["id"], "odoo_purchase": "P00013"})
            self.assertIn("estado 'draft'", result.reason)
            result = run_workflow(self.dispatch, "orders.confirm", {"order_id": order["id"], "odoo_purchase": "P00012"})
            self.assertTrue(result.ok, result.reason)
        self.assertEqual(result.data["state"], "confirmed")
        mirror = M_odoo_purchase.objects.get(name="P00012")
        self.assertEqual((mirror.odoo_id, mirror.partner_name, mirror.state), (12, "UMA S.A.S.", "purchase"))
        self.assertEqual(M_odoo_sync_log.objects.filter(operation="get_purchase", status="success").count(), 1)
        self.assertEqual(sum(1 for service, _ in fake.calls if service == "common"), 1)  # uid en caché

    def test_delivered_order_is_notified_to_odoo(self):
        fake = FakeOdoo([purchase()])
        with mock.patch("apps.apiOdoo.repository.apiOdoo.requests.post", side_effect=fake), \
                self.captureOnCommitCallbacks(execute=True):
            order = self.requested_order()
            run_workflow(self.dispatch, "orders.confirm", {"order_id": order["id"], "odoo_purchase": "P00012"})
            trip = run_workflow(self.dispatch, "trips.build", {
                "company_id": self.uma.id, "origin_address_id": self.warehouse.id,
                "allocations": [{"order_line_id": order["lines"][0]["id"], "qty": "10"}],
            }).data
            run_workflow(self.dispatch, "trips.assign",
                         {"trip_id": trip["id"], "vehicle_id": self.vehicle.id, "driver_id": self.driver.id})
            run_workflow(self.driver_user, "trips.depart", {"trip_id": trip["id"]})
            result = run_workflow(self.driver_user, "trips.deliver",
                                  {"trip_id": trip["id"], "trip_line_id": trip["lines"][0]["id"]}, files=[proof_file()])
            self.assertTrue(result.ok, result.reason)
        posts = [args for service, args in fake.calls if service == "object" and args[4] == "message_post"]
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0][5], [[12]])
        self.assertIn(order["code"], posts[0][6]["body"])
        self.assertTrue(M_odoo_sync_log.objects.filter(operation="notify_delivery", status="success").exists())

    def test_sync_partners_creates_and_updates_companies(self):
        fake = FakeOdoo(partners=[
            {"id": 40, "name": "Concesionario Nuevo", "vat": "901.555.111-3", "email": "a@b.co", "phone": "1"},
            {"id": 41, "name": "UMA Colombia", "vat": "901", "email": "", "phone": ""},  # ya existe por NIT
            {"id": 42, "name": "Sin NIT", "vat": False},
        ])
        with mock.patch("apps.apiOdoo.repository.apiOdoo.requests.post", side_effect=fake):
            self.assertIn("Permisos faltantes", run_workflow(self.dispatch, "apiOdoo.get_create_partners").reason)
            result = run_workflow(self.admin, "apiOdoo.get_create_partners")
        self.assertTrue(result.ok, result.reason)
        self.assertEqual((result.data["created"], result.data["updated"], len(result.data["skipped"])), (1, 1, 1))
        new = M_company.objects.get(document_number="901555111")
        self.assertEqual((new.verification_digit, new.odoo_ref), ("3", "40"))
        self.uma.refresh_from_db()
        self.assertEqual((self.uma.name, self.uma.odoo_ref), ("UMA Colombia", "41"))

    @override_settings(ODOO_URL="")
    def test_missing_configuration_is_reported(self):
        result = run_workflow(self.dispatch, "apiOdoo.get_purchase", {"name": "P00012"})
        self.assertIn("Falta configurar Odoo: ODOO_URL", result.reason)
