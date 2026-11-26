"""Alta de empresa con su administrador y gestión de la empresa, por los workflows del motor."""

from decimal import Decimal

from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from enginedj.base.models import M_company, M_user_company

from apps.locations.models import M_location
from apps.orders.models import M_type_item
from apps.testing import build_world, client_for, run_workflow

ADMIN_PASSWORD = "Distri-2026!x"


class CompanyFlowTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        build_world(cls)
        cls.city = M_location.objects.get(code_dane="20001")
        cls.materials = M_type_item.objects.get(name="Materiales")

    def ok(self, result):
        self.assertTrue(result.ok, result.reason)
        return result.data

    def create_company(self, user=None, nit="900500", admin=True, **company):
        payload = {"company": {"name": "Distritodo", "document_number": nit, **company}}
        if admin:
            payload["admin"] = {"username": f"admin_{nit}", "first_name": "Ana", "email": "ana@distritodo.co",
                                "password": ADMIN_PASSWORD}
        return run_workflow(user or self.admin, "companies.create", payload)

    def company_admin(self, nit="900500"):
        company = self.ok(self.create_company(nit=nit))
        return company, User.objects.get(username=f"admin_{nit}")

    # ------------------------------------------------------------------
    def test_hurgo_admin_creates_company_with_its_admin(self):
        company = self.ok(self.create_company())
        self.assertEqual((company["name"], company["is_client"], company["admin"]["role"]),
                         ("Distritodo", True, "admin_empresa"))
        admin = User.objects.get(username="admin_900500")
        self.assertTrue(admin.check_password(ADMIN_PASSWORD))
        self.assertTrue(M_user_company.objects.filter(user_id=admin, company_id=company["id"]).exists())
        # Puede iniciar sesión y ve la empresa que administra
        login = client_for(None).post("/api/auth/token/", {"username": "admin_900500", "password": ADMIN_PASSWORD},
                                      format="json")
        self.assertEqual(login.status_code, 200)
        mine = self.ok(run_workflow(admin, "companies.mine"))
        self.assertEqual([c["id"] for c in mine["companies"]], [company["id"]])
        listed = self.ok(run_workflow(self.admin, "companies.list"))
        self.assertIn("admin_900500", next(c for c in listed if c["id"] == company["id"])["admins"])

    def test_only_hurgo_admin_creates_and_nit_is_unique(self):
        for user in (self.dispatch, self.commercial):
            self.assertFalse(self.create_company(user=user).ok)
        self.ok(self.create_company(admin=False))
        self.assertIn("Ya existe una empresa", self.create_company(nit="900500").reason)
        # Siempre queda como cliente (pide y guarda sus direcciones de entrega)
        self.ok(self.create_company(nit="900501", admin=False))
        self.assertTrue(M_company.objects.get(document_number="900501").is_client)

    def test_weak_password_rolls_back_everything(self):
        r = run_workflow(self.admin, "companies.create", {
            "company": {"name": "X", "document_number": "900600"},
            "admin": {"username": "admin_x", "password": "123"},
        })
        self.assertFalse(r.ok)
        self.assertFalse(M_company.objects.filter(document_number="900600").exists())
        self.assertFalse(User.objects.filter(username="admin_x").exists())

    def test_company_admin_manages_users_of_own_company_only(self):
        company, admin = self.company_admin()
        seller = self.ok(run_workflow(admin, "companies.user.save", {
            "company_id": company["id"], "username": "vendedor_dt", "password": "Vende-2026!x", "role": "comercial"}))
        self.assertEqual(seller["role"], "comercial")
        self.ok(run_workflow(admin, "companies.user.save", {
            "company_id": company["id"], "username": "factura_dt", "password": "Factu-2026!x", "role": "facturador"}))
        users = self.ok(run_workflow(admin, "companies.users", {"company_id": company["id"]}))
        self.assertEqual(sorted(u["username"] for u in users), ["admin_900500", "factura_dt", "vendedor_dt"])

        # Roles de Hurgo no se pueden asignar
        for role in ("despacho", "administracion", "conductor"):
            r = run_workflow(admin, "companies.user.save", {
                "company_id": company["id"], "user_id": seller["id"], "role": role})
            self.assertIn("Rol no permitido", r.reason)
        # Desactivar a un usuario de su empresa
        seller = self.ok(run_workflow(admin, "companies.user.save", {
            "company_id": company["id"], "user_id": seller["id"], "role": "comercial", "is_active": False}))
        self.assertFalse(seller["is_active"])
        # No puede quitarse el rol de admin
        r = run_workflow(admin, "companies.user.save", {"company_id": company["id"], "user_id": admin.id,
                                                        "role": "comercial"})
        self.assertIn("No puedes quitarte", r.reason)
        # Otra empresa: ni ve ni edita sus usuarios
        self.assertFalse(run_workflow(admin, "companies.users", {"company_id": self.uma.id}).ok)
        r = run_workflow(admin, "companies.user.save", {
            "company_id": company["id"], "user_id": self.commercial.id, "role": "comercial"})
        self.assertIn("no pertenece", r.reason)
        # El comercial de la empresa no administra usuarios
        self.assertFalse(run_workflow(User.objects.get(username="factura_dt"), "companies.users",
                                      {"company_id": company["id"]}).ok)

    def test_company_admin_manages_addresses_and_products_and_orders(self):
        company, admin = self.company_admin()
        address = self.ok(run_workflow(admin, "locations.address.save", {
            "company_id": company["id"], "location_id": self.city.id, "name": "Bodega", "address": "Cl 9"}))
        self.assertEqual(address["company_id"], company["id"])
        self.assertEqual(len(self.ok(run_workflow(admin, "locations.addresses", {"company_id": company["id"]}))), 1)
        self.assertFalse(run_workflow(admin, "locations.addresses", {"company_id": self.uma.id}).ok)
        self.assertFalse(run_workflow(admin, "locations.address.save", {
            "company_id": self.uma.id, "location_id": self.city.id, "name": "X", "address": "Y"}).ok)

        # Sus tipos y unidades los crea la empresa (Hurgo no)
        materials = self.ok(run_workflow(admin, "catalogs.save", {"catalog": "type_item", "name": "Materiales"}))
        self.ok(run_workflow(admin, "catalogs.save", {"catalog": "unit", "name": "Bulto", "symbol": "bulto"}))
        self.assertIn("no existe o es de otra empresa", run_workflow(admin, "orders.item.save", {
            "company_id": company["id"], "type_item_id": self.materials.id, "name": "X"}).reason)
        item = self.ok(run_workflow(admin, "orders.item.save", {
            "company_id": company["id"], "type_item_id": materials["id"], "name": "Cemento gris", "unit": "bulto",
            "weight_kg": "50", "sku": "CEM-1"}))
        self.assertEqual((item["name"], Decimal(item["weight_kg"])), ("Cemento gris", Decimal("50")))
        self.assertIn("Ya existe un producto", run_workflow(admin, "orders.item.save", {
            "company_id": company["id"], "type_item_id": materials["id"], "name": "Otro", "sku": "CEM-1"}).reason)
        self.assertFalse(run_workflow(admin, "orders.item.save", {
            "company_id": self.uma.id, "type_item_id": materials["id"], "name": "X"}).ok)
        # Hurgo no crea productos, direcciones ni usuarios de la empresa
        self.assertFalse(run_workflow(self.admin, "orders.item.save", {
            "company_id": company["id"], "type_item_id": materials["id"], "name": "De Hurgo"}).ok)
        self.assertFalse(run_workflow(self.admin, "locations.address.save", {
            "company_id": company["id"], "location_id": self.city.id, "name": "De Hurgo", "address": "X"}).ok)
        self.assertFalse(run_workflow(self.admin, "companies.user.save", {
            "company_id": company["id"], "username": "de_hurgo", "password": "Hurgo-2026!x", "role": "comercial"}).ok)
        self.assertFalse(run_workflow(admin, "orders.company_items", {"company_id": self.uma.id}).ok)

        # Hace lo del comercial: pide con su producto, y solo ve sus pedidos
        order = self.ok(run_workflow(admin, "orders.create", {"lines": [
            {"item_id": item["id"], "qty": "5", "address_id": address["id"]}]}))
        self.assertEqual(order["company"]["id"], company["id"])
        listing = {"data": {"fields": ["id", "code"], "limit": 50}}
        self.assertEqual([o["id"] for o in self.ok(run_workflow(admin, "orders.list", listing))], [order["id"]])
        # El stock solo lo ve Hurgo; la empresa solo ve sus solicitudes de compra
        self.assertFalse(run_workflow(admin, "stock.requirements", {"company_id": company["id"]}).ok)
        self.assertFalse(run_workflow(admin, "stock.list").ok)
        self.assertEqual(self.ok(run_workflow(admin, "stock.purchase_request.list")), [])
        lookups = self.ok(run_workflow(admin, "locations.lookups"))
        self.assertEqual([c["id"] for c in lookups["companies"]], [company["id"]])


class IdentifyTests(APITestCase):
    """Paso 1 del login: respuesta neutra (no revela si el usuario existe ni si está activo)."""

    @classmethod
    def setUpTestData(cls):
        build_world(cls)
        cls.inactive = User.objects.create_user("inactivo", password="x-Clave-2026")
        cls.inactive.is_active = False
        cls.inactive.save()
        M_user_company.objects.create(user_id=cls.inactive, company_id=cls.uma)

    def identify(self, username):
        response = client_for(None).post("/api/auth/identify/", {"username": username}, format="json")
        self.assertEqual(response.status_code, 200)
        return response.data

    def test_known_user_of_one_company_gets_its_brand(self):
        self.assertEqual(self.identify("COMERCIAL")["company"]["name"], "UMA")

    def test_unknown_inactive_or_without_company_look_the_same(self):
        expected = {"company": None}
        for username in ("no-existe", "inactivo", "despacho"):
            self.assertEqual(self.identify(username), expected, username)
