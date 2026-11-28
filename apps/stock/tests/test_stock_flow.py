"""Flujo de materiales con stock (Distritodo) por los workflows del motor, con Odoo simulado.

Pedido de 200 bolsas -> necesidad de compra (200 - stock 100 = 100) -> solicitud al facturador ->
compra en Odoo -> stock -> lugar de cargue -> viaje que carga desde el stock -> cancelación / devolución.
"""

import shutil
import tempfile
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.test import override_settings
from rest_framework.test import APITestCase

from enginedj.base.models import M_company, M_user_company
from enginedj.notification.models import M_notification

from apps.locations.models import M_loading_tag, M_location
from apps.orders.models import M_company_address, M_item, M_order_line, M_type_item, M_unit
from apps.stock.models import M_stock, M_stock_move
from apps.companies.tenancy import create_company_schema
from apps.testing import in_company, PASSWORD, build_world, proof_file, run_workflow

MEDIA_ROOT = tempfile.mkdtemp()

# Compras "en Odoo": nombre -> (cabecera, líneas)
ODOO = {}


def odoo_purchase(odoo_id, name, lines, state="purchase"):
    ODOO[name] = (
        {"id": odoo_id, "name": name, "state": state, "partner_id": [7, "Argos"], "date_order": "2026-11-20 10:00:00",
         "amount_total": 1000, "order_line": [line[0] for line in lines]},
        [{"id": line_id, "order_id": [odoo_id, name], "product_id": [product, f"Producto {product}"],
          "name": f"Producto {product}", "product_qty": qty, "qty_received": 0, "product_uom": [1, "Bulto"]}
         for line_id, product, qty in lines],
    )


class FakeOdoo:
    def __init__(self, *args, **kwargs):
        pass

    def get_purchase(self, name):
        return ODOO[name][0] if name in ODOO else None

    def get_purchase_lines(self, purchase_odoo_id):
        return next(lines for head, lines in ODOO.values() if head["id"] == purchase_odoo_id)


@override_settings(MEDIA_ROOT=MEDIA_ROOT, ODOO_ENABLED=True)
@patch("apps.apiOdoo.services.S_odoo_purchase.ApiOdooService", FakeOdoo)
class StockFlowTests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)

    @classmethod
    def setUpTestData(cls):
        build_world(cls)
        cls.cement_uma_id = cls.cement.id  # cemento de UMA (tipo sin stock), antes de usar el de Distritodo
        city = M_location.objects.get(code_dane="20001")
        cls.distritodo = M_company.objects.create(name="Distritodo", document_number="950", is_client=True)
        create_company_schema(cls.distritodo)
        cls.argos = M_company.objects.create(name="Argos", document_number="952")
        cls.tag_cement = M_loading_tag.objects.create(name="Cemento")  # central (logística de Hurgo)

        with in_company(cls.distritodo):  # sus datos viven en su esquema
            cls.store_addr = M_company_address.objects.create(company_id=cls.distritodo, location_id=city,
                                                              name="Ferretería San Sebastián", address="Cra 5")
            stock_type = M_type_item.objects.create(company_id=cls.distritodo, name="Materiales con stock",
                                                    uses_stock=True)
            M_unit.objects.create(company_id=cls.distritodo, symbol="bulto", name="Bulto")
            cls.cement = M_item.objects.create(company_id=cls.distritodo, type_item_id=stock_type,
                                               name="Cemento gris", unit="bulto", weight_kg=Decimal("50"),
                                               odoo_ref="501")
            cls.brick = M_item.objects.create(company_id=cls.distritodo, type_item_id=stock_type, name="Ladrillo",
                                              odoo_ref="502")
            cls.cement.loading_tags.add(cls.tag_cement)

        def user(username, role):
            u = User.objects.create_user(username, f"{username}@test.co", PASSWORD)
            u.groups.add(Group.objects.get(name=role))
            M_user_company.objects.create(user_id=u, company_id=cls.distritodo)
            return u

        cls.dt_commercial = user("comercial_dt", "comercial")
        cls.biller = user("facturador_dt", "facturador")

        ODOO.clear()
        odoo_purchase(1, "P00001", [(11, 501, 100)])
        odoo_purchase(2, "P00002", [(21, 501, 100), (22, 999, 5)])  # 999: producto sin emparejar
        odoo_purchase(3, "P00003", [(31, 501, 10)], state="draft")

    # ------------------------------------------------------------------
    def ok(self, result):
        self.assertTrue(result.ok, result.reason)
        return result.data

    def stock(self, item=None):
        with in_company(self.distritodo):
            row = M_stock.objects.filter(company_id=self.distritodo, item_id=item or self.cement).first()
            return row.qty_available if row else Decimal("0")

    def request(self, qty, order_line=None, user=None):
        return run_workflow(user or self.dispatch, "stock.purchase_request.create", {
            "company_id": self.distritodo.id,
            "lines": [{"item_id": self.cement.id, "qty": str(qty),
                       **({"order_line_id": order_line} if order_line else {})}],
        })

    def link(self, request_id, name, user=None):
        return run_workflow(user or self.biller, "stock.purchase_request.link_purchase",
                            {"purchase_request_id": request_id, "odoo_purchase": name})

    def loading_point(self, name="Planta Argos", tag_ids=None):
        return self.ok(run_workflow(self.dispatch, "locations.loading_point.save", {
            "company_id": self.argos.id, "location_id": self.store_addr.location_id_id, "name": name,
            "address": "Km 3 vía a Bosconia", "tag_ids": tag_ids if tag_ids is not None else [self.tag_cement.id],
        }))

    def order(self, qty=200, loading=None):
        order = self.ok(run_workflow(self.dt_commercial, "orders.create", {
            "lines": [{"item_id": self.cement.id, "qty": str(qty), "address_id": self.store_addr.id}],
        }))
        if loading:
            order = self.ok(run_workflow(self.dispatch, "orders.set_loading_point", {
                "order_id": order["id"], "address_id": loading["id"], "company_id": self.distritodo.id}))
        return self.ok(run_workflow(self.dispatch, "orders.confirm",
                                    {"order_id": order["id"], "company_id": self.distritodo.id}))

    def requirement(self):
        rows = self.ok(run_workflow(self.dispatch, "stock.requirements", {"company_id": self.distritodo.id}))
        return next(r for r in rows if r["item_id"] == self.cement.id)

    def initial_stock(self):
        """Una compra anterior dejó 100 bolsas disponibles."""
        req = self.ok(self.request(100))
        self.ok(self.link(req["id"], "P00001"))
        self.assertEqual(self.stock(), Decimal("100"))

    # ------------------------------------------------------------------
    def test_full_flow_buys_only_what_is_missing_and_loads_from_stock(self):
        self.initial_stock()
        plant = self.loading_point()

        # 1. El punto de venta pide 200 bolsas para San Sebastián, sin lugar de cargue
        order = self.ok(run_workflow(self.dt_commercial, "orders.create", {
            "lines": [{"item_id": self.cement.id, "qty": "200", "address_id": self.store_addr.id}],
        }))
        self.assertIsNone(order["address"])
        line_id = order["lines"][0]["id"]

        # 2. Necesidad de compra: 200 pendientes - 100 en stock = 100
        req = self.requirement()
        self.assertEqual((Decimal(req["pending"]), Decimal(req["available"]), Decimal(req["to_buy"])),
                         (Decimal("200"), Decimal("100"), Decimal("100")))

        # 3. Solicitud al facturador (queda notificado) y ya no se pide dos veces
        request = self.ok(self.request(req["to_buy"], order_line=line_id))
        self.assertTrue(request["code"].startswith("SC-"))
        self.assertEqual((request["state"], request["lines"][0]["order_code"]), ("sent", order["code"]))
        self.assertTrue(M_notification.objects.filter(user_to_id=self.biller, title__contains=request["code"]).exists())
        self.assertEqual(Decimal(self.requirement()["to_buy"]), Decimal("0"))

        # 4-5. El facturador registra la compra de Odoo: entra al stock (una sola vez)
        linked = self.ok(self.link(request["id"], "P00002"))
        self.assertEqual(linked["state"], "purchased")
        self.assertEqual([p["name"] for p in linked["odoo_purchases"]], ["P00002"])
        self.assertEqual(linked["stock_summary"]["unmatched"][0]["odoo_line_id"], 22)
        self.assertEqual(self.stock(), Decimal("200"))
        self.ok(self.link(request["id"], "P00002"))
        self.assertEqual(self.stock(), Decimal("200"))

        # 6. Hurgo elige el lugar de cargue (sugerido por la etiqueta Cemento) y confirma sin compra
        points = self.ok(run_workflow(self.dispatch, "locations.loading_points",
                                      {"order_id": order["id"], "order_company_id": self.distritodo.id}))
        self.assertEqual((points[0]["id"], points[0]["suggested"], points[0]["matching_tags"]),
                         (plant["id"], True, ["Cemento"]))
        self.ok(run_workflow(self.dispatch, "orders.set_loading_point",
                             {"order_id": order["id"], "address_id": plant["id"], "company_id": self.distritodo.id}))
        order = self.ok(run_workflow(self.dispatch, "orders.confirm",
                                     {"order_id": order["id"], "company_id": self.distritodo.id}))
        self.assertEqual((order["state"], order["address"]["id"], order["odoo_purchase"]),
                         ("confirmed", plant["id"], ""))

        # Al armar el viaje, despacho ve el stock disponible en la línea pendiente
        pending = self.ok(run_workflow(self.dispatch, "orders.pending_lines", {"company_id": self.distritodo.id}))
        self.assertEqual(Decimal(next(p for p in pending if p["id"] == line_id)["stock_available"]), Decimal("200"))

        # 7. Viaje: carga 150 desde el stock; el origen es el lugar de cargue del pedido; 50 quedan pendientes
        trip = self.ok(run_workflow(self.dispatch, "trips.build", {
            "company_id": self.distritodo.id, "allocations": [{"order_line_id": line_id, "qty": "150"}],
        }))
        self.assertEqual(trip["origin_address"], "Planta Argos")
        self.assertEqual(self.stock(), Decimal("50"))
        with in_company(self.distritodo):
            line = M_order_line.objects.get(pk=line_id)
        self.assertEqual((line.state, line.qty_pending), ("partial", Decimal("50")))

        # No se carga más de lo que hay en stock (otro pedido de 100 con el mismo cargue; solo quedan 50)
        order2 = self.order(100, loading=plant)
        r = run_workflow(self.dispatch, "trips.add_allocations", {
            "trip_id": trip["id"], "allocations": [{"order_line_id": order2["lines"][0]["id"], "qty": "60"}],
        })
        self.assertFalse(r.ok)
        self.assertIn("solo hay 50", r.reason)
        self.assertEqual(self.stock(), Decimal("50"))

        # 10. Si el viaje se cancela, las bolsas vuelven al stock y al pedido
        self.ok(run_workflow(self.dispatch, "trips.cancel", {"trip_id": trip["id"], "reason": "Sin camión"}))
        self.assertEqual(self.stock(), Decimal("200"))
        with in_company(self.distritodo):
            line.refresh_from_db()
        self.assertEqual(line.state, "pending")

        moves = self.ok(run_workflow(self.dispatch, "stock.moves", {"company_id": self.distritodo.id}))
        self.assertEqual([m["move_type"] for m in reversed(moves)],
                         ["purchase_in", "purchase_in", "trip_out", "trip_cancel_in"])
        self.assertEqual(moves[1]["trip_code"], trip["code"])
        self.assertEqual(Decimal(moves[0]["balance"]), Decimal("200"))

    def test_returned_stop_gives_stock_back(self):
        self.initial_stock()
        order = self.order(80, loading=self.loading_point())
        line_id = order["lines"][0]["id"]
        trip = self.ok(run_workflow(self.dispatch, "trips.build", {
            "company_id": self.distritodo.id, "allocations": [{"order_line_id": line_id, "qty": "80"}],
        }))
        self.assertEqual(self.stock(), Decimal("20"))
        self.ok(run_workflow(self.dispatch, "trips.assign",
                             {"trip_id": trip["id"], "vehicle_id": self.vehicle.id, "driver_id": self.driver.id}))
        run_workflow(self.driver_user, "trips.accept", {"trip_id": trip["id"]})
        trip = self.ok(run_workflow(self.driver_user, "trips.depart", {"trip_id": trip["id"]}))
        self.ok(run_workflow(self.driver_user, "trips.register_return",
                             {"trip_id": trip["id"], "trip_line_id": trip["lines"][0]["id"], "reason": "Cerrado"},
                             files=[proof_file()]))
        self.assertEqual(self.stock(), Decimal("100"))
        with in_company(self.distritodo):
            self.assertTrue(M_stock_move.objects.filter(move_type="return_in", qty=Decimal("80")).exists())

    def test_one_loading_point_per_trip(self):
        self.initial_stock()
        o1 = self.order(10, loading=self.loading_point("Planta A"))
        o2 = self.order(10, loading=self.loading_point("Planta B"))
        allocations = [{"order_line_id": o1["lines"][0]["id"], "qty": "10"},
                       {"order_line_id": o2["lines"][0]["id"], "qty": "10"}]
        r = run_workflow(self.dispatch, "trips.build", {"company_id": self.distritodo.id, "allocations": allocations})
        self.assertFalse(r.ok)
        self.assertIn("lugares distintos", r.reason)
        self.assertEqual(self.stock(), Decimal("100"))

    def test_order_without_loading_point_needs_trip_origin(self):
        self.initial_stock()
        order = self.order(10)
        r = run_workflow(self.dispatch, "trips.build", {
            "company_id": self.distritodo.id, "allocations": [{"order_line_id": order["lines"][0]["id"], "qty": "5"}],
        })
        self.assertIn("lugar de cargue", r.reason)

    def test_purchase_must_be_confirmed_in_odoo(self):
        req = self.ok(self.request(10))
        r = self.link(req["id"], "P00003")
        self.assertFalse(r.ok)
        self.assertIn("debe estar confirmada", r.reason)
        self.assertEqual(self.stock(), Decimal("0"))

    def test_permissions_and_scope(self):
        # El comercial no pide compras ni ve stock; el facturador solo ve su empresa
        self.assertFalse(self.request(10, user=self.dt_commercial).ok)
        self.assertFalse(run_workflow(self.dt_commercial, "stock.list").ok)
        self.assertFalse(run_workflow(self.biller, "stock.list").ok)  # el stock solo lo ve Hurgo
        req = self.ok(self.request(10))
        self.assertEqual(len(self.ok(run_workflow(self.biller, "stock.purchase_request.list"))), 1)
        self.assertFalse(run_workflow(self.biller, "stock.requirements", {"company_id": self.uma.id}).ok)
        # Productos sin stock (cemento de UMA, tipo Materiales normal) no van en solicitudes
        r = run_workflow(self.dispatch, "stock.purchase_request.create", {
            "company_id": self.uma.id, "lines": [{"item_id": self.cement_uma_id, "qty": "1"}],
        })
        self.assertIn("no se maneja con stock", r.reason)
        self.assertEqual(req["state"], "sent")
        # Solo despacho registra lugares de cargue
        r = run_workflow(self.dt_commercial, "locations.loading_point.save", {
            "company_id": self.argos.id, "location_id": self.store_addr.location_id_id, "name": "X", "address": "Y",
        })
        self.assertFalse(r.ok)
