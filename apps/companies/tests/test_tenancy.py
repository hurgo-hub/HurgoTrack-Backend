"""Un esquema de PostgreSQL por empresa: se crea al dar de alta la empresa y aísla sus datos."""

from datetime import date

from django.contrib.auth.models import Group, User
from django.db import connection
from django_tenants.utils import schema_context
from rest_framework.test import APITestCase

from enginedj.base.cache import cache_get, cache_set
from enginedj.base.exceptions import BusinessPermissionError
from enginedj.base.models import M_user_company

from apps.companies.models import M_tenant
from apps.companies.tenancy import company_schema
from apps.orders.models import M_company_address, M_item, M_order
from apps.testing import build_world, in_company, run_workflow


def schemas():
    with connection.cursor() as cur:
        cur.execute("select schema_name from information_schema.schemata")
        return {r[0] for r in cur.fetchall()}


def tables(schema):
    with connection.cursor() as cur:
        cur.execute("select table_name from information_schema.tables where table_schema = %s", [schema])
        return {r[0] for r in cur.fetchall()}


class TenancyTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        build_world(cls)

    def create(self, nit, name):
        result = run_workflow(self.admin, "companies.create", {"company": {"name": name, "document_number": nit},
                                                                "admin": {"username": f"adm{nit}",
                                                                          "password": "Clave-Fuerte-2026"}})
        self.assertTrue(result.ok, result.reason)
        return result.data

    def test_creating_a_company_creates_its_schema_with_its_tables(self):
        company = self.create("800100", "Distritodo")
        tenant = M_tenant.objects.get(company_id=company["id"])
        self.assertEqual(tenant.schema_name, f"c{company['id']}")
        self.assertIn(tenant.schema_name, schemas())
        self.assertTrue({"item", "orders", "order_line", "stock", "unit", "purchase_request"} <= tables(tenant.schema_name))
        # Lo central (usuarios, viajes, empresas) no se copia al esquema de la empresa
        self.assertFalse({"auth_user", "trip", "company"} & tables(tenant.schema_name))

    def test_company_user_cannot_enter_another_company_schema(self):
        a = self.create("800200", "Empresa A")
        b = self.create("800300", "Empresa B")
        user_a = User.objects.get(username="adm800200")
        with company_schema(a["id"], user_a):
            self.assertEqual(connection.schema_name, f"c{a['id']}")
        with self.assertRaises(BusinessPermissionError):
            with company_schema(b["id"], user_a):
                pass
        with company_schema(b["id"], self.dispatch):  # Hurgo sí entra al de cualquier empresa
            self.assertEqual(connection.schema_name, f"c{b['id']}")

    def test_cache_is_separated_by_schema(self):
        a = self.create("800400", "Empresa C")
        b = self.create("800500", "Empresa D")
        with schema_context(f"c{a['id']}"):
            cache_set("orders.order", "list", ["de A"], q=1)
        with schema_context(f"c{b['id']}"):
            self.assertIsNone(cache_get("orders.order", "list", q=1))
        with schema_context(f"c{a['id']}"):
            self.assertEqual(cache_get("orders.order", "list", q=1), ["de A"])

    def test_company_data_does_not_exist_in_another_schema(self):
        with in_company(self.uma):
            self.assertTrue(M_item.objects.filter(name="Cemento").exists())
            self.assertEqual(M_order.objects.count(), 3)
        with in_company(self.akt):
            self.assertFalse(M_item.objects.filter(name="Cemento").exists())
            self.assertFalse(M_company_address.objects.filter(name="Concesionario 1").exists())
            self.assertEqual(M_order.objects.count(), 0)
        # En el esquema central no hay pedidos ni productos
        self.assertNotIn("orders", tables("public"))
        self.assertNotIn("item", tables("public"))

    def test_company_user_cannot_reach_another_company_even_sending_its_id(self):
        akt = self.other_commercial
        for name, data in (("orders.list", {}), ("orders.retrieve", {"order_id": self.order1.id}),
                           ("orders.cancel", {"order_id": self.order1.id})):
            result = run_workflow(akt, name, {**data, "company_id": self.uma.id})
            self.assertFalse(result.ok, name)
            self.assertIn("Solo puedes acceder a los datos de tu empresa", result.reason, name)
        # Sin company_id trabaja en su esquema, donde ese pedido no existe
        self.assertIn("no existe", run_workflow(akt, "orders.retrieve", {"order_id": self.order1.id}).reason)
        self.assertEqual(run_workflow(akt, "orders.list").data, [])

    def test_hurgo_lists_orders_of_every_company(self):
        with in_company(self.akt):
            M_order.objects.create(company_id=self.akt, address_id=self.warehouse, order_date=date.today(),
                                   state="requested")
        rows = run_workflow(self.dispatch, "orders.list").data
        self.assertEqual(sorted(r["company_id"] for r in rows), sorted([self.uma.id] * 3 + [self.akt.id]))
        # Con company_id ve solo los de esa empresa
        rows = run_workflow(self.dispatch, "orders.list", {"company_id": self.akt.id}).data
        self.assertEqual(len(rows), 1)
