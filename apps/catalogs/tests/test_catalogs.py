"""Catálogos: cada empresa crea sus tipos, unidades, marcas y documentos; Hurgo solo los de logística."""

from django.contrib.auth.models import Group, User
from rest_framework.test import APITestCase

from enginedj.base.models import M_user_company

from apps.testing import build_world, run_workflow
from apps.trips.models import M_trip_type_attach


class CatalogTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        build_world(cls)
        cls.uma_admin = User.objects.create_user("admin_uma", password="x-Clave-2026")
        cls.uma_admin.groups.add(Group.objects.get(name="admin_empresa"))
        M_user_company.objects.create(user_id=cls.uma_admin, company_id=cls.uma)
        cls.akt_admin = User.objects.create_user("admin_akt", password="x-Clave-2026")
        cls.akt_admin.groups.add(Group.objects.get(name="admin_empresa"))
        M_user_company.objects.create(user_id=cls.akt_admin, company_id=cls.akt)

    def ok(self, result):
        self.assertTrue(result.ok, result.reason)
        return result.data

    def save(self, user, catalog, **data):
        return run_workflow(user, "catalogs.save", {"catalog": catalog, **data})

    def rows(self, user, catalog):
        return self.ok(run_workflow(user, "catalogs.list", {"catalog": catalog}))

    def test_each_company_has_its_own_types_units_and_brands(self):
        self.ok(self.save(self.uma_admin, "type_item", name="Repuestos", uses_stock=True))
        self.ok(self.save(self.uma_admin, "unit", name="Caja", symbol="caja"))
        self.ok(self.save(self.uma_admin, "brand", name="Yamaha"))
        # El mismo nombre en otra empresa sí; repetido en la misma, no
        self.ok(self.save(self.akt_admin, "type_item", name="Repuestos"))
        self.assertIn("Ya existe", self.save(self.uma_admin, "type_item", name="Repuestos").reason)
        # Cada empresa ve solo lo suyo
        self.assertEqual({r["name"] for r in self.rows(self.uma_admin, "unit")}, {"Caja", "Bulto"})
        self.assertEqual({r["name"] for r in self.rows(self.akt_admin, "unit")}, set())
        akt_type = next(r for r in self.rows(self.akt_admin, "type_item") if r["name"] == "Repuestos")
        self.assertIn("no es tuyo", self.save(self.uma_admin, "type_item", id=akt_type["id"], name="X").reason)

    def test_hurgo_does_not_create_company_catalogs(self):
        tabs = {c["key"] for c in self.ok(run_workflow(self.admin, "catalogs.available"))}
        self.assertNotIn("unit", tabs)
        self.assertIn("loading_tag", tabs)
        self.assertIn("lo gestiona cada empresa", self.save(self.admin, "unit", name="Galón", symbol="gal").reason)
        self.assertIn("lo gestiona cada empresa", self.save(self.admin, "brand", name="X").reason)
        # Y la empresa no toca los de logística
        self.assertIn("lo gestiona Hurgo", self.save(self.uma_admin, "loading_tag", name="Cemento").reason)
        self.assertFalse(self.save(self.commercial, "brand", name="X").ok)  # el comercial no gestiona catálogos
        self.ok(self.save(self.admin, "type_vehicle", name="Tractomula"))

    def test_company_documents_and_hurgo_process_documents(self):
        doc = self.ok(self.save(self.uma_admin, "document_type", name="Factura", stage="order", is_required=True))
        self.assertEqual(M_trip_type_attach.objects.get(pk=doc["id"]).company_id_id, self.uma.id)
        # La empresa ve sus documentos y, solo para leer, los del proceso de Hurgo
        rows = {r["name"]: r for r in self.rows(self.uma_admin, "document_type")}
        self.assertFalse(rows["Factura"]["read_only"])
        self.assertTrue(rows["Remisión firmada"]["read_only"])
        self.assertIn("Valor inválido", self.save(self.uma_admin, "document_type", name="X", stage="otra").reason)
        # Hurgo ve y edita solo los del proceso; no puede desactivar los que usa el sistema
        hurgo = {r["name"]: r for r in self.rows(self.admin, "process_document_type")}
        self.assertNotIn("Factura", hurgo)
        self.assertIn("no se puede desactivar", self.save(
            self.admin, "process_document_type", id=hurgo["Remisión firmada"]["id"], name="Remisión firmada",
            is_active=False).reason)

    def test_products_use_own_catalogs_only(self):
        akt_unit = self.ok(self.save(self.akt_admin, "unit", name="Saco", symbol="saco"))
        type_id = self.ok(self.save(self.uma_admin, "type_item", name="Áridos"))["id"]
        r = run_workflow(self.uma_admin, "orders.item.save", {
            "company_id": self.uma.id, "type_item_id": type_id, "name": "Arena", "unit_id": akt_unit["id"]})
        self.assertIn("unidad no existe o es de otra empresa", r.reason)
        own = self.ok(self.save(self.uma_admin, "unit", name="Saco", symbol="saco"))
        item = self.ok(run_workflow(self.uma_admin, "orders.item.save", {
            "company_id": self.uma.id, "type_item_id": type_id, "name": "Arena", "unit_id": own["id"]}))
        self.assertEqual((item["unit"], item["unit_name"]), ("saco", "Saco"))
