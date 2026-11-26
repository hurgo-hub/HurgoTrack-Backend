"""Flota desde la app: Hurgo registra propietarios, vehículos, SOAT, RTM y conductores con su usuario."""

import shutil
import tempfile
from datetime import date, timedelta

from django.contrib.auth.models import Group, User
from django.test import override_settings
from rest_framework.test import APITestCase

from enginedj.base.models import M_company, M_user_company

from apps.drivers.models import M_driver
from apps.fleet.models import M_brand_vehicle, M_type_vehicle, M_vehicle
from apps.testing import build_world, client_for, proof_file, run_workflow

MEDIA_ROOT = tempfile.mkdtemp()
PASSWORD = "Conduce-2026!x"


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class FleetAdminTests(APITestCase):
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
        cls.truck = M_type_vehicle.objects.get(name="Camión")
        cls.chevrolet = M_brand_vehicle.objects.get(name="Chevrolet")

    def ok(self, result):
        self.assertTrue(result.ok, result.reason)
        return result.data

    def new_vehicle(self, plate="xyz-98 7", **extra):
        owner = self.ok(run_workflow(self.admin, "fleet.partner.save", {
            "name": "Transportes Pérez", "document_number": "1.065.222", "phone": "300"}))
        return self.ok(run_workflow(self.admin, "fleet.vehicle.save", {
            "plate": plate, "type_vehicle_id": self.truck.id, "brand_vehicle_id": self.chevrolet.id,
            "owner_id": owner["id"], "license_category": "B2", "load_capacity_kg": "3000", "model_year": 2015,
            **extra}))

    def test_hurgo_registers_vehicle_with_soat_and_rtm(self):
        vehicle = self.new_vehicle()
        self.assertEqual((vehicle["plate"], vehicle["owner"], vehicle["soat"], vehicle["rtm_required"]),
                         ("XYZ987", "Transportes Pérez", None, True))
        self.assertEqual(M_vehicle.objects.get(pk=vehicle["id"]).company_id, self.hurgo)  # flota de Hurgo
        self.assertIn("Ya existe un vehículo con la placa XYZ987", run_workflow(self.admin, "fleet.vehicle.save", {
            "plate": "XYZ987", "type_vehicle_id": self.truck.id, "brand_vehicle_id": self.chevrolet.id,
            "owner_id": vehicle["owner_id"]}).reason)
        # Edición parcial: quitar la capacidad (vacío) sin tocar lo demás
        edited = self.ok(run_workflow(self.admin, "fleet.vehicle.save",
                                      {"vehicle_id": vehicle["id"], "load_capacity_kg": "", "color": "Blanco"}))
        self.assertEqual((edited["load_capacity_kg"], edited["color"], edited["plate"]), (None, "Blanco", "XYZ987"))

        today = date.today()
        self.assertIn("posterior al vencimiento", run_workflow(self.admin, "fleet.soat.save", {
            "vehicle_id": vehicle["id"], "insurer_name": "Sura", "policy_number": "P-1",
            "date_start": str(today), "date_expire": str(today - timedelta(days=1))}).reason)
        soat = self.ok(run_workflow(self.admin, "fleet.soat.save", {
            "vehicle_id": vehicle["id"], "insurer_name": "Sura", "policy_number": "P-1",
            "date_expire": str(today + timedelta(days=300))}, files=[proof_file("soat.pdf")]))
        self.assertEqual((soat["valid"], soat["file_name"]), (True, "soat.pdf"))
        self.ok(run_workflow(self.admin, "fleet.rtm.save", {
            "vehicle_id": vehicle["id"], "certificate_number": "R-9", "cda_name": "CDA Valledupar",
            "date_expedition": str(today), "date_expire": str(today + timedelta(days=365))}))
        row = next(v for v in self.ok(run_workflow(self.dispatch, "fleet.vehicles")) if v["id"] == vehicle["id"])
        self.assertEqual((row["soat"]["policy_number"], row["rtm"]["certificate_number"]), ("P-1", "R-9"))

    def test_only_hurgo_administration_manages_the_fleet(self):
        # Despacho consulta pero no registra
        self.ok(run_workflow(self.dispatch, "fleet.vehicles"))
        self.assertFalse(run_workflow(self.dispatch, "fleet.partner.save", {"name": "X", "document_number": "1"}).ok)
        # Una empresa cliente no ve ni registra flota
        for name, data in (("fleet.vehicles", {}), ("drivers.list", {}),
                           ("fleet.partner.save", {"name": "X", "document_number": "1"})):
            self.assertFalse(run_workflow(self.uma_admin, name, data).ok, name)
            self.assertFalse(run_workflow(self.commercial, name, data).ok, name)

    def test_missing_hurgo_company_is_reported(self):
        M_company.objects.filter(pk=self.hurgo.pk).update(is_active=False)
        self.assertIn("Falta la empresa Hurgo", run_workflow(self.admin, "fleet.partner.save", {
            "name": "X", "document_number": "1"}).reason)

    def test_new_driver_gets_a_user_and_can_be_assigned(self):
        driver = self.ok(run_workflow(self.admin, "drivers.save", {
            "username": "pedro", "password": PASSWORD, "first_name": "Pedro", "last_name": "Gómez",
            "document_number": "1065999", "phone": "3001112233", "license_number": "LIC-77",
            "license_category": "C2", "license_expire": str(date.today() + timedelta(days=400))}))
        self.assertEqual((driver["name"], driver["document_number"], driver["license_number"], driver["license_valid"]),
                         ("Pedro Gómez", "1065999", "LIC77", True))
        pedro = User.objects.get(username="pedro")
        self.assertTrue(pedro.groups.filter(name="conductor").exists())
        self.assertEqual(M_driver.objects.get(pk=driver["id"]).company_id, self.hurgo)
        # Entra a la app y ve sus viajes (ninguno todavía)
        login = client_for(None).post("/api/auth/token/", {"username": "pedro", "password": PASSWORD}, format="json")
        self.assertEqual(login.status_code, 200)
        self.assertEqual(self.ok(run_workflow(pedro, "trips.mine")), [])
        # Licencia repetida y edición
        self.assertIn("Ya existe un conductor con la licencia LIC77", run_workflow(self.admin, "drivers.save", {
            "username": "otro", "password": PASSWORD, "license_number": "lic 77", "license_category": "B1"}).reason)
        edited = self.ok(run_workflow(self.admin, "drivers.save", {"driver_id": driver["id"], "phone": "315",
                                                                   "is_available": False}))
        self.assertEqual((edited["phone"], edited["is_available"]), ("315", False))
        # Un usuario de Hurgo que ya existe también puede volverse conductor, pero no dos veces
        self.assertIn("ya es conductor", run_workflow(self.admin, "drivers.save", {
            "user_id": pedro.id, "license_number": "LIC-88", "license_category": "B1"}).reason)

    def test_vehicle_and_driver_registered_in_the_app_take_a_trip(self):
        vehicle = self.new_vehicle(plate="TRK100")
        driver = self.ok(run_workflow(self.admin, "drivers.save", {
            "username": "luis", "password": PASSWORD, "first_name": "Luis", "license_number": "LIC-55",
            "license_category": "B2", "license_expire": str(date.today() + timedelta(days=200))}))
        trip = self.ok(run_workflow(self.dispatch, "trips.build", {
            "company_id": self.uma.id, "origin_address_id": self.warehouse.id,
            "allocations": [{"order_line_id": self.l_cement.id, "qty": "10"}]}))
        assign = {"trip_id": trip["id"], "vehicle_id": vehicle["id"], "driver_id": driver["id"]}
        self.assertIn("no tiene SOAT vigente", run_workflow(self.dispatch, "trips.assign", assign).reason)
        today = date.today()
        self.ok(run_workflow(self.admin, "fleet.soat.save", {
            "vehicle_id": vehicle["id"], "insurer_name": "Sura", "policy_number": "P-2",
            "date_expire": str(today + timedelta(days=100))}))
        self.assertIn("técnico-mecánica", run_workflow(self.dispatch, "trips.assign", assign).reason)
        self.ok(run_workflow(self.admin, "fleet.rtm.save", {
            "vehicle_id": vehicle["id"], "certificate_number": "R-1", "cda_name": "CDA",
            "date_expedition": str(today), "date_expire": str(today + timedelta(days=100))}))
        self.assertEqual(self.ok(run_workflow(self.dispatch, "trips.assign", assign))["state"], "assigned")
