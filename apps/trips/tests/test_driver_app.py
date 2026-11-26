"""Lo que hace la app móvil del conductor: login por cookies, refresh, trips.mine y logout."""

from datetime import timedelta
from decimal import Decimal

from django.test import override_settings
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.settings import api_settings as jwt_settings

from apps.testing import PASSWORD, build_world
from apps.trips.models import M_trip, M_trip_line


class DriverAppTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        build_world(cls)
        cls.trip = M_trip.objects.create(company_id=cls.uma, carrier_id=cls.hurgo, vehicle_id=cls.vehicle,
                                         driver_id=cls.driver, origin_address_id=cls.warehouse, state="assigned")
        M_trip_line.objects.create(trip_id=cls.trip, sequence=1, recipient_id=cls.uma, address_id=cls.dealer_addr,
                                   qty=Decimal("3"), state="delivered")
        M_trip_line.objects.create(trip_id=cls.trip, sequence=2, recipient_id=cls.uma,
                                   address_id=cls.dealer2_addr, qty=Decimal("2"))

    def login(self):
        client = APIClient()
        r = client.post("/api/auth/token/", {"username": "conductor", "password": PASSWORD}, format="json")
        self.assertEqual(r.status_code, 200)
        return client, r

    def test_dev_cookies_work_over_http(self):
        """En local (http, emulador 10.0.2.2) la cookie no es Secure: si lo fuera, el teléfono no la reenvía."""
        _, r = self.login()
        access, refresh = r.cookies["access_token"], r.cookies["refresh_token"]
        self.assertEqual((access["secure"], access["samesite"], access["httponly"]), ("", "Lax", True))
        self.assertEqual(int(access["max-age"]), int(jwt_settings.ACCESS_TOKEN_LIFETIME.total_seconds()))
        self.assertEqual(int(refresh["max-age"]), int(jwt_settings.REFRESH_TOKEN_LIFETIME.total_seconds()))

    @override_settings(SIMPLE_JWT={"ACCESS_TOKEN_LIFETIME": timedelta(minutes=5), "AUTH_COOKIE_SECURE": True,
                                   "AUTH_COOKIE_SAMESITE": "None"})
    def test_production_cookies_are_secure(self):
        _, r = self.login()
        self.assertEqual((r.cookies["access_token"]["secure"], r.cookies["access_token"]["samesite"]),
                         (True, "None"))

    def test_refresh_keeps_working_with_rotation(self):
        """ROTATE_REFRESH_TOKENS + blacklist: cada refresh guarda el refresh nuevo en la cookie."""
        client, r = self.login()
        first_refresh = r.cookies["refresh_token"].value
        for _ in range(3):
            r = client.post("/api/auth/token/refresh/")
            self.assertEqual(r.status_code, 200, r.data)
            self.assertIn("refresh_token", r.cookies)
        self.assertNotEqual(client.cookies["refresh_token"].value, first_refresh)
        self.assertEqual(client.get("/api/auth/session/status/").status_code, 200)

        stale = APIClient()
        stale.cookies["refresh_token"] = first_refresh  # el viejo quedó en la blacklist
        self.assertEqual(stale.post("/api/auth/token/refresh/").status_code, 401)

    def test_profile_and_my_trips_summary(self):
        client, _ = self.login()
        profile = client.get("/api/auth/user/").data
        self.assertIn("trips.drive_trip", profile["permissions"])

        r = client.post("/api/workflows/sync/trips.mine/", {}, format="json")
        self.assertTrue(r.data["success"], r.data)
        (trip,) = r.data["details"]["context"]["results"]
        self.assertEqual(trip["code"], self.trip.code)
        self.assertEqual((trip["stops_total"], trip["stops_done"], trip["total_qty"]), (2, 1, "5.00"))
        self.assertEqual(trip["destination"]["name"], "Concesionario 2")
        self.assertEqual(trip["origin_location"], "Valledupar")

    def test_logout_deletes_cookies(self):
        client, _ = self.login()
        r = client.post("/api/auth/logout/")
        self.assertEqual(r.cookies["access_token"]["max-age"], 0)
        self.assertEqual(r.cookies["access_token"]["samesite"], "Lax")
        self.assertEqual(client.get("/api/auth/session/status/").status_code, 401)
