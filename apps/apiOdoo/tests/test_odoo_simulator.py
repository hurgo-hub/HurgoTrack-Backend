"""Odoo simulado (ODOO_SIMULATED=True): comprar sin un Odoo real y seguir el flujo normal hasta el stock."""

from django.test import override_settings
from rest_framework.test import APITestCase

from apps.apiOdoo.models import M_odoo_purchase
from apps.testing import build_world, in_company, run_workflow

SIMULATED = {"ODOO_SIMULATED": True, "ODOO_ENABLED": True, "ODOO_URL": ""}


class OdooSimulatorTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        build_world(cls)
        with in_company(cls.uma):  # el cemento de UMA se maneja con stock y tiene su referencia en Odoo
            cls.materials.uses_stock = True
            cls.materials.save()
            cls.cement.odoo_ref = "501"
            cls.cement.save()

    def ok(self, result):
        self.assertTrue(result.ok, result.reason)
        return result.data

    def purchase_request(self, qty="10"):
        return self.ok(run_workflow(self.dispatch, "stock.purchase_request.create", {
            "company_id": self.uma.id, "lines": [{"item_id": self.cement.id, "qty": qty}]}))

    def stock(self):
        rows = self.ok(run_workflow(self.dispatch, "stock.list", {"company_id": self.uma.id}))
        return next((r["qty_available"] for r in rows if r["item_id"] == self.cement.id), "0.00")

    def test_simulator_is_off_by_default(self):
        self.assertEqual(self.ok(run_workflow(self.dispatch, "apiOdoo.mode")), {"enabled": False, "simulated": False})
        request = self.purchase_request()
        self.assertIn("simulador de Odoo está apagado", run_workflow(self.dispatch, "apiOdoo.simulate_purchase", {
            "company_id": self.uma.id, "purchase_request_id": request["id"]}).reason)

    @override_settings(**SIMULATED)
    def test_simulated_purchase_enters_stock_like_a_real_one(self):
        self.assertTrue(self.ok(run_workflow(self.dispatch, "apiOdoo.mode"))["simulated"])
        request = self.purchase_request("40")
        sim = self.ok(run_workflow(self.dispatch, "apiOdoo.simulate_purchase", {
            "company_id": self.uma.id, "purchase_request_id": request["id"]}))
        self.assertEqual((sim["name"], sim["lines"]), (f"SIM-{request['code']}", [{"product": "Cemento", "qty": "40.00"}]))
        # Se registra con el flujo normal, como una compra real de Odoo
        linked = self.ok(run_workflow(self.dispatch, "stock.purchase_request.link_purchase", {
            "company_id": self.uma.id, "purchase_request_id": request["id"], "odoo_purchase": sim["name"]}))
        self.assertEqual(linked["state"], "purchased")
        self.assertEqual(self.stock(), "40.00")
        # Registrarla otra vez no suma de nuevo; otra simulación tiene otra referencia
        self.ok(run_workflow(self.dispatch, "stock.purchase_request.link_purchase", {
            "company_id": self.uma.id, "purchase_request_id": request["id"], "odoo_purchase": sim["name"]}))
        self.assertEqual(self.stock(), "40.00")
        again = self.ok(run_workflow(self.dispatch, "apiOdoo.simulate_purchase", {
            "company_id": self.uma.id, "purchase_request_id": request["id"]}))
        self.assertEqual(again["name"], f"SIM-{request['code']}-2")
        # Una referencia que el simulador no tiene "no existe en Odoo"
        self.assertIn("no existe en Odoo", run_workflow(self.dispatch, "stock.purchase_request.link_purchase", {
            "company_id": self.uma.id, "purchase_request_id": request["id"], "odoo_purchase": "P00099"}).reason)
        # Las compras simuladas quedan en el esquema de la empresa
        with in_company(self.uma):
            self.assertTrue(M_odoo_purchase.objects.filter(name=sim["name"], raw__simulated=True).exists())
        with in_company(self.akt):
            self.assertFalse(M_odoo_purchase.objects.exists())

    @override_settings(**SIMULATED)
    def test_products_need_their_odoo_reference(self):
        with in_company(self.uma):
            self.cement.odoo_ref = ""
            self.cement.save()
        request = self.purchase_request()
        self.assertIn("Ref. Odoo", run_workflow(self.dispatch, "apiOdoo.simulate_purchase", {
            "company_id": self.uma.id, "purchase_request_id": request["id"]}).reason)

    @override_settings(**SIMULATED)
    def test_order_without_stock_is_confirmed_with_a_simulated_purchase(self):
        order = self.ok(run_workflow(self.commercial, "orders.create", {
            "address_id": self.warehouse.id, "lines": [{"item_id": self.moto.id, "qty": "2",
                                                        "address_id": self.dealer_addr.id}]}))
        sim = self.ok(run_workflow(self.dispatch, "apiOdoo.simulate_purchase", {
            "company_id": self.uma.id, "order_id": order["id"]}))
        confirmed = self.ok(run_workflow(self.dispatch, "orders.confirm", {
            "company_id": self.uma.id, "order_id": order["id"], "odoo_purchase": sim["name"]}))
        self.assertEqual((confirmed["state"], confirmed["odoo_purchase"]), ("confirmed", sim["name"]))
