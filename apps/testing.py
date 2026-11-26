"""Escenario de prueba compartido por los tests de pedidos y viajes."""

import os
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from rest_framework.test import APIClient

from enginedj.base.models import M_company, M_user_company

from apps.drivers.models import M_driver
from apps.fleet.models import M_brand_vehicle, M_mechanical_inspection, M_partner, M_soat, M_type_vehicle, M_vehicle
from apps.companies.tenancy import create_company_schema, tenant_schema
from apps.locations.models import M_address, M_location
from apps.orders.models import M_brand, M_company_address, M_item, M_order, M_order_line, M_type_item, M_unit

PASSWORD = "Clave-123"


def in_company(company):
    """Entra al esquema de la empresa (para leer o crear sus datos con el ORM en los tests)."""
    from django_tenants.utils import schema_context

    return schema_context(tenant_schema(company.pk if hasattr(company, "pk") else company))


def make_stop(trip, sequence, address, **fields):
    """Parada de prueba con la copia de la dirección de entrega (como la arma S_trip)."""
    from apps.trips.models import M_trip_line

    stop = M_trip_line(trip_id=trip, sequence=sequence, recipient_id=trip.company_id, **fields)
    stop.copy_address(address)
    stop.save()
    return stop


def proof_file(name="remision.jpg"):
    return SimpleUploadedFile(name, b"\xff\xd8\xff fake jpeg", content_type="image/jpeg")


def client_for(user):
    client = APIClient()
    if user is not None:
        client.force_authenticate(user)
    return client


class WorkflowResult:
    def __init__(self, response):
        self.status_code = response.status_code
        body = response.data
        self.ok = bool(body.get("success"))
        details = body.get("details") or {}
        self.data = (details.get("context") or {}).get("results")
        self.reason = details.get("reason") or ""

    def __repr__(self):
        return f"<WorkflowResult ok={self.ok} reason={self.reason!r}>"


def run_workflow(user, name, data=None, files=None) -> WorkflowResult:
    """Ejecuta un workflow como lo hace el frontend: POST /api/workflows/sync/<name>/."""
    client = client_for(user)
    url = f"/api/workflows/sync/{name}/"
    if files:
        response = client.post(url, {**(data or {}), "files": files}, format="multipart")
    else:
        response = client.post(url, data or {}, format="json")
    return WorkflowResult(response)


def build_world(t):
    """Crea el escenario y lo deja como atributos de ``t`` (la clase de test en setUpTestData).

    - Hurgo (transportador), UMA (cliente con comercial), AKT (otro cliente). UMA y AKT tienen su
      propio esquema (``c<id>``): sus catálogos, productos, direcciones y pedidos se crean ahí.
      Para leerlos con el ORM en un test: ``with in_company(t.uma): ...``.
    - ``warehouse``: lugar de cargue (central, de Hurgo) "Bodega UMA".
    - Las direcciones de entrega son de la empresa que pide: UMA guarda "Concesionario 1" y
      "Concesionario 2" (``dealer_addr`` / ``dealer2_addr``); AKT tiene ``akt_addr``.
    - Motos UMA (serializadas, 120 kg), motos de otra marca y cemento (50 kg).
    - order1: UMA -> concesionario 1 (2 motos + 10 cementos); order2: -> concesionario 2 (1 moto);
      order3: -> concesionario 1 (1 moto de otra marca). Los tres confirmados, cargue en la bodega UMA.
    - Camión C2 con SOAT y RTM vigentes; conductor C2 y conductor2 B1.
    """
    with open(os.devnull, "w") as devnull:
        call_command("seed_workflows", stdout=devnull)
    today = date.today()

    def user(username, role=None):  # role = nombre del grupo que crea seed_workflows
        u = User.objects.create_user(username, f"{username}@test.co", PASSWORD, first_name=username.title())
        if role:
            u.groups.add(Group.objects.get(name=role))
        return u

    t.dispatch = user("despacho", "despacho")
    t.commercial = user("comercial", "comercial")
    t.other_commercial = user("otro_comercial", "comercial")
    t.driver_user = user("conductor", "conductor")
    t.driver2_user = user("conductor2", "conductor")
    t.superuser = User.objects.create_superuser("root", "root@test.co", PASSWORD)
    t.admin = user("administrador", "administracion")

    t.hurgo = M_company.objects.create(name="Hurgo", document_number="900", is_carrier=True)
    t.uma = M_company.objects.create(name="UMA", document_number="901", is_client=True)
    t.akt = M_company.objects.create(name="AKT", document_number="902", is_client=True)
    M_user_company.objects.create(user_id=t.commercial, company_id=t.uma)
    M_user_company.objects.create(user_id=t.other_commercial, company_id=t.akt)
    for company in (t.uma, t.akt):
        create_company_schema(company)

    # Departamentos y municipios oficiales: los carga seed_workflows (DIVIPOLA); no se crean
    city = M_location.objects.get(code_dane="20001")  # Valledupar, Cesar
    t.city = city
    t.warehouse = M_address.objects.create(company_id=t.uma, name="Bodega UMA", address="Cl 1", location_id=city)
    with in_company(t.akt):
        t.akt_addr = M_company_address.objects.create(company_id=t.akt, name="Bodega AKT", address="Cl 4",
                                                      location_id=city)
        akt_materials = M_type_item.objects.create(company_id=t.akt, name="Materiales")
        t.akt_item = M_item.objects.create(company_id=t.akt, type_item_id=akt_materials, name="Arena AKT")
    with in_company(t.uma):
        _uma_world(t, city, today)
    _hurgo_fleet(t, today)


def _uma_world(t, city, today):
    t.dealer_addr = M_company_address.objects.create(company_id=t.uma, name="Concesionario 1", address="Cl 2",
                                                     location_id=city)
    t.dealer2_addr = M_company_address.objects.create(company_id=t.uma, name="Concesionario 2", address="Cl 3",
                                                      location_id=city)
    motos = M_type_item.objects.create(company_id=t.uma, name="Motos", is_serialized=True)
    materials = M_type_item.objects.create(company_id=t.uma, name="Materiales")
    t.materials = materials
    brand_uma = M_brand.objects.create(name="UMA", company_id=t.uma)
    brand_other = M_brand.objects.create(name="Otra", company_id=t.uma)
    t.moto = M_item.objects.create(company_id=t.uma, type_item_id=motos, brand_id=brand_uma, name="UMA 125",
                                   weight_kg=Decimal("120"), is_vehicle=True, is_serialized=True)
    t.moto_other = M_item.objects.create(company_id=t.uma, type_item_id=motos, brand_id=brand_other,
                                         name="Otra 150", is_vehicle=True, is_serialized=True)
    M_unit.objects.create(company_id=t.uma, symbol="bulto", name="Bulto")  # las unidades son de cada empresa
    t.cement = M_item.objects.create(company_id=t.uma, type_item_id=materials, name="Cemento", unit="bulto",
                                     weight_kg=Decimal("50"))

    def order(address, *lines):
        o = M_order.objects.create(company_id=t.uma, address_id=t.warehouse, order_date=today, state="confirmed")
        return o, [M_order_line.objects.create(order_id=o, item_id=item, recipient_id=t.uma, address_id=address,
                                               qty=Decimal(qty)) for item, qty in lines]

    t.order1, (t.l_moto, t.l_cement) = order(t.dealer_addr, (t.moto, 2), (t.cement, 10))
    t.order2, (t.l_moto2,) = order(t.dealer2_addr, (t.moto, 1))
    t.order3, (t.l_other,) = order(t.dealer_addr, (t.moto_other, 1))


def _hurgo_fleet(t, today):
    owner = M_partner.objects.create(company_id=t.hurgo, name="Propietario", document_number="123")
    t.vehicle = M_vehicle.objects.create(
        company_id=t.hurgo, plate="ABC123", brand_vehicle_id=M_brand_vehicle.objects.create(name="Chevrolet"),
        type_vehicle_id=M_type_vehicle.objects.create(name="Camión"), owner_id=owner, license_category="C2",
        load_capacity_kg=Decimal("5000"), motorcycle_capacity=10, model_year=2018,
    )
    M_soat.objects.create(vehicle_id=t.vehicle, insurer_name="S", policy_number="1",
                          date_expire=today + timedelta(days=100))
    M_mechanical_inspection.objects.create(vehicle_id=t.vehicle, certificate_number="R1", cda_name="CDA",
                                           date_expedition=today, date_expire=today + timedelta(days=100))
    t.driver = M_driver.objects.create(company_id=t.hurgo, user_id=t.driver_user, license_number="L1",
                                       license_category="C2", license_expire=today + timedelta(days=365))
    t.driver2 = M_driver.objects.create(company_id=t.hurgo, user_id=t.driver2_user, license_number="L2",
                                        license_category="B1")
