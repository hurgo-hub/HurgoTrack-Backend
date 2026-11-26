"""Departamentos y municipios oficiales (DIVIPOLA): los carga seed_workflows y nadie los crea ni edita."""

import os

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase

from apps.locations.divipola import display_name, load
from apps.locations.models import M_location


class DivipolaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        with open(os.devnull, "w") as devnull:
            call_command("seed_workflows", stdout=devnull)

    def test_official_departments_and_municipalities(self):
        self.assertEqual(M_location.objects.filter(location_type="department").count(), 33)
        self.assertEqual(M_location.objects.filter(location_type="municipality").count(), 1122)
        city = M_location.objects.select_related("parent_id").get(code_dane="20001")
        self.assertEqual((city.name, city.parent_id.name, city.parent_id.code_dane), ("Valledupar", "Cesar", "20"))
        self.assertEqual(M_location.objects.get(code_dane="47692").name, "San Sebastián de Buenavista")

    def test_seed_is_idempotent(self):
        summary = load()
        self.assertEqual((summary["created"], summary["updated"]), (0, 0))
        self.assertEqual(M_location.objects.filter(code_dane="20001").count(), 1)

    def test_display_name(self):
        self.assertEqual(display_name("BOGOTÁ, D.C."), "Bogotá, D.C.")
        self.assertEqual(display_name("EL CARMEN DE VIBORAL"), "El Carmen de Viboral")

    def test_admin_is_read_only(self):
        root = User.objects.create_superuser("root", "root@test.co", "x-Clave-2026")
        self.client.force_login(root)
        self.assertEqual(self.client.get("/admin/locations/m_location/add/").status_code, 403)
        city = M_location.objects.get(code_dane="20001")
        response = self.client.post(f"/admin/locations/m_location/{city.pk}/change/", {"name": "Otra"})
        self.assertIn(response.status_code, (403, 200))
        city.refresh_from_db()
        self.assertEqual(city.name, "Valledupar")
