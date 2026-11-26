"""Documentos requeridos por etapa: pedido (confirmar), cargue (salir), entrega (entregar) y flota (asignar)."""

import shutil
import tempfile
from datetime import date, timedelta

from django.contrib.auth.models import Group, User
from django.test import override_settings
from rest_framework.test import APITestCase

from enginedj.base.models import M_user_company

from apps.testing import build_world, proof_file, run_workflow

MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class DocumentTests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)

    @classmethod
    def setUpTestData(cls):
        build_world(cls)
        cls.uma_admin = User.objects.create_user("admin_uma", password="x-Clave-2026")
        cls.uma_admin.groups.add(Group.objects.get(name="admin_empresa"))
        M_user_company.objects.create(user_id=cls.uma_admin, company_id=cls.uma)

    def ok(self, result):
        self.assertTrue(result.ok, result.reason)
        return result.data

    def doc_type(self, user, catalog, **data):
        return self.ok(run_workflow(user, "catalogs.save", {"catalog": catalog, **data}))

    def test_order_documents_required_to_confirm(self):
        factura = self.doc_type(self.uma_admin, "document_type", name="Factura", stage="order", is_required=True)
        order = self.ok(run_workflow(self.commercial, "orders.create", {
            "address_id": self.warehouse.id, "lines": [{"item_id": self.cement.id, "qty": "5",
                                                        "address_id": self.dealer_addr.id}]}))
        r = run_workflow(self.dispatch, "orders.confirm", {"order_id": order["id"], "odoo_purchase": "PO-1"})
        self.assertIn("Faltan documentos del pedido: Factura", r.reason)
        # Otra empresa no sube documentos a este pedido
        self.assertFalse(run_workflow(self.other_commercial, "orders.attach", {
            "order_id": order["id"], "type_attach_id": factura["id"]}, files=[proof_file()]).ok)
        docs = self.ok(run_workflow(self.commercial, "orders.attach", {
            "order_id": order["id"], "type_attach_id": factura["id"]}, files=[proof_file("factura.pdf")]))
        self.assertEqual(len(next(d for d in docs if d["id"] == factura["id"])["files"]), 1)
        self.ok(run_workflow(self.dispatch, "orders.confirm", {"order_id": order["id"], "odoo_purchase": "PO-1"}))

    def ready_trip(self):
        trip = self.ok(run_workflow(self.dispatch, "trips.build", {
            "company_id": self.uma.id, "origin_address_id": self.warehouse.id,
            "allocations": [{"order_line_id": self.l_cement.id, "qty": "10"}]}))
        return self.ok(run_workflow(self.dispatch, "trips.assign", {
            "trip_id": trip["id"], "vehicle_id": self.vehicle.id, "driver_id": self.driver.id}))

    def test_loading_and_delivery_documents(self):
        rows = self.ok(run_workflow(self.admin, "catalogs.list", {"catalog": "process_document_type"}))
        loading = next(r for r in rows if r["stage"] == "loading")
        self.doc_type(self.admin, "process_document_type", id=loading["id"], name=loading["name"],
                      stage="loading", is_required=True)
        acta = self.doc_type(self.uma_admin, "document_type", name="Acta de entrega", stage="delivery",
                             is_required=True)
        trip = self.ready_trip()

        # Cargue: sin la foto de cargue no sale; el otro conductor no la puede subir
        self.assertIn("Faltan documentos de cargue", run_workflow(
            self.driver_user, "trips.depart", {"trip_id": trip["id"]}).reason)
        self.assertFalse(run_workflow(self.driver2_user, "trips.attach", {
            "trip_id": trip["id"], "type_attach_id": loading["id"]}, files=[proof_file()]).ok)
        self.ok(run_workflow(self.driver_user, "trips.attach", {
            "trip_id": trip["id"], "type_attach_id": loading["id"]}, files=[proof_file()]))
        trip = self.ok(run_workflow(self.driver_user, "trips.depart", {"trip_id": trip["id"]}))

        # Entrega: el acta de la empresa va antes de la remisión, en esa parada
        stop = trip["lines"][0]
        deliver = {"trip_id": trip["id"], "trip_line_id": stop["id"]}
        self.assertIn("faltan documentos de entrega: Acta de entrega", run_workflow(
            self.driver_user, "trips.deliver", deliver, files=[proof_file()]).reason)
        self.assertIn("Indica la parada", run_workflow(self.driver_user, "trips.attach", {
            "trip_id": trip["id"], "type_attach_id": acta["id"]}, files=[proof_file()]).reason)
        docs = self.ok(run_workflow(self.driver_user, "trips.attach", {
            **deliver, "type_attach_id": acta["id"]}, files=[proof_file()]))
        self.assertEqual(len(docs["delivery"][0]["documents"][0]["files"]), 1)
        self.assertEqual(self.ok(run_workflow(self.driver_user, "trips.deliver", deliver,
                                              files=[proof_file()]))["state"], "closed")

    def test_required_fleet_documents_block_assignment(self):
        poliza = self.doc_type(self.admin, "fleet_document_type", name="Póliza de carga", applies_to="vehicle",
                               is_required=True, has_expiration=True)
        trip = self.ok(run_workflow(self.dispatch, "trips.build", {
            "company_id": self.uma.id, "origin_address_id": self.warehouse.id,
            "allocations": [{"order_line_id": self.l_cement.id, "qty": "10"}]}))
        assign = {"trip_id": trip["id"], "vehicle_id": self.vehicle.id, "driver_id": self.driver.id}
        self.assertIn("no tiene vigentes: Póliza de carga", run_workflow(self.dispatch, "trips.assign", assign).reason)
        upload = {"vehicle_id": self.vehicle.id, "type_id": poliza["id"]}
        self.assertIn("vencimiento", run_workflow(self.admin, "fleet.document.upload", upload,
                                                  files=[proof_file()]).reason)
        self.ok(run_workflow(self.admin, "fleet.document.upload",
                             {**upload, "date_expire": str(date.today() - timedelta(days=1))}, files=[proof_file()]))
        self.assertIn("no tiene vigentes", run_workflow(self.dispatch, "trips.assign", assign).reason)  # vencida
        docs = self.ok(run_workflow(self.admin, "fleet.document.upload",
                                    {**upload, "date_expire": str(date.today() + timedelta(days=90))},
                                    files=[proof_file()]))
        self.assertTrue(docs[0]["ok"])
        self.ok(run_workflow(self.dispatch, "trips.assign", assign))
