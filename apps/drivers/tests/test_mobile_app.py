"""App del conductor: login con token, celular para notificaciones, aviso al asignar y aceptar / rechazar."""

from unittest import mock

from django.test import override_settings
from rest_framework.test import APIClient, APITestCase

from apps.drivers.models import M_device
from apps.testing import PASSWORD, build_world, run_workflow

TOKEN = "ExponentPushToken[abc123]"


class ExpoResponse:
    def __init__(self, tickets):
        self.tickets = tickets

    def raise_for_status(self):
        return None

    def json(self):
        return {"data": self.tickets}


class MobileAppTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        build_world(cls)

    def ok(self, result):
        self.assertTrue(result.ok, result.reason)
        return result.data

    def login(self, username, password=PASSWORD):
        return APIClient().post("/api/mobile/auth/token/", {"username": username, "password": password},
                                format="json")

    def bearer(self, access):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        return client

    def workflow(self, client, name, data=None):
        body = client.post(f"/api/workflows/sync/{name}/", data or {}, format="json").json()
        return body.get("success"), (body.get("details") or {})

    def build_trip(self):
        return self.ok(run_workflow(self.dispatch, "trips.build", {
            "company_id": self.uma.id, "origin_address_id": self.warehouse.id,
            "allocations": [{"order_line_id": self.l_cement.id, "qty": "10"}]}))

    def assign(self, trip, driver=None):
        return self.ok(run_workflow(self.dispatch, "trips.assign", {
            "trip_id": trip["id"], "vehicle_id": self.vehicle.id, "driver_id": (driver or self.driver).id}))

    # ------------------------------------------------------------------
    def test_only_drivers_log_in_to_the_app_and_use_bearer_tokens(self):
        self.assertEqual(self.login("conductor", "mala").status_code, 401)
        for username in ("comercial", "despacho"):
            response = self.login(username)
            self.assertEqual(response.status_code, 403, username)
            self.assertIn("app es para conductores", response.json()["detail"])
        response = self.login("conductor")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["driver"]["id"], self.driver.id)
        # Con el token en el encabezado usa los mismos workflows que la web
        self.assign(self.build_trip())
        success, details = self.workflow(self.bearer(body["access"]), "trips.mine")
        self.assertTrue(success)
        self.assertEqual(len(details["context"]["results"]), 1)
        self.assertFalse(self.workflow(self.bearer("token-falso"), "trips.mine")[0])

    def test_refresh_rotates_and_a_deactivated_driver_loses_the_session(self):
        first = self.login("conductor").json()
        renewed = APIClient().post("/api/mobile/auth/refresh/", {"refresh": first["refresh"]}, format="json")
        self.assertEqual(renewed.status_code, 200)
        self.assertNotEqual(renewed.json()["refresh"], first["refresh"])
        # El refresh viejo ya no sirve (se usa una sola vez)
        again = APIClient().post("/api/mobile/auth/refresh/", {"refresh": first["refresh"]}, format="json")
        self.assertEqual(again.status_code, 401)
        self.driver.is_active = False
        self.driver.save()
        cut = APIClient().post("/api/mobile/auth/refresh/", {"refresh": renewed.json()["refresh"]}, format="json")
        self.assertEqual(cut.status_code, 403)

    @override_settings(PUSH_ENABLED=True, CELERY_TASK_ALWAYS_EAGER=True)
    def test_driver_gets_a_push_when_a_trip_is_assigned(self):
        access = self.login("conductor").json()["access"]
        success, _ = self.workflow(self.bearer(access), "mobile.device.register",
                                   {"push_token": TOKEN, "app_version": "1.0.0"})
        self.assertTrue(success)
        self.assertFalse(self.workflow(self.bearer(access), "mobile.device.register", {"push_token": "x"})[0])
        trip = self.build_trip()
        with mock.patch("requests.post", return_value=ExpoResponse([{"status": "ok"}])) as post, \
                self.captureOnCommitCallbacks(execute=True):
            self.assign(trip)
        message = post.call_args.kwargs["json"][0]
        self.assertEqual((message["to"], message["title"]), (TOKEN, "Nuevo viaje asignado"))
        self.assertIn(trip["code"], message["body"])
        self.assertEqual(message["data"], {"kind": "trip_assigned", "trip_id": trip["id"], "trip_code": trip["code"]})
        # Si Expo dice que el celular ya no existe, deja de enviarle
        with mock.patch("requests.post", return_value=ExpoResponse(
                [{"status": "error", "details": {"error": "DeviceNotRegistered"}}])), \
                self.captureOnCommitCallbacks(execute=True):
            self.ok(run_workflow(self.dispatch, "trips.cancel", {"trip_id": trip["id"], "reason": "Prueba"}))
        self.assertFalse(M_device.objects.get(push_token=TOKEN).is_active)

    def test_no_push_when_disabled(self):
        self.ok(run_workflow(self.driver_user, "mobile.device.register", {"push_token": TOKEN}))
        with mock.patch("requests.post") as post, self.captureOnCommitCallbacks(execute=True):
            self.assign(self.build_trip())
        post.assert_not_called()

    def test_driver_accepts_or_rejects_the_trip(self):
        trip = self.assign(self.build_trip())
        # Solo el conductor asignado responde
        self.assertFalse(run_workflow(self.driver2_user, "trips.accept", {"trip_id": trip["id"]}).ok)
        self.assertFalse(run_workflow(self.dispatch, "trips.accept", {"trip_id": trip["id"]}).ok)
        self.assertIn("por qué", run_workflow(self.driver_user, "trips.reject",
                                              {"trip_id": trip["id"], "reason": " "}).reason)
        rejected = self.ok(run_workflow(self.driver_user, "trips.reject",
                                        {"trip_id": trip["id"], "reason": "Tengo el camión varado"}))
        self.assertEqual(rejected["state"], "draft")
        # Vuelve a despacho sin vehículo ni conductor y con el motivo
        seen = self.ok(run_workflow(self.dispatch, "trips.retrieve", {"trip_id": trip["id"]}))
        self.assertEqual((seen["vehicle"], seen["driver"], seen["driver_response"]), (None, None, "rejected"))
        self.assertIn("Tengo el camión varado", seen["driver_response_note"])
        self.assertEqual(self.ok(run_workflow(self.driver_user, "trips.mine")), [])
        # Al asignarlo de nuevo, el nuevo conductor tiene que aceptar
        trip = self.assign(trip)
        self.assertEqual((trip["driver_response"], trip["driver_response_note"]), ("", ""))
        accepted = self.ok(run_workflow(self.driver_user, "trips.accept", {"trip_id": trip["id"]}))
        self.assertEqual(accepted["driver_response"], "accepted")
        self.assertEqual(self.ok(run_workflow(self.driver_user, "trips.depart", {"trip_id": trip["id"]}))["state"],
                         "in_route")
        # Ya en ruta no se rechaza
        self.assertFalse(run_workflow(self.driver_user, "trips.reject", {"trip_id": trip["id"], "reason": "x"}).ok)
