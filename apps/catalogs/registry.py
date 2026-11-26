"""Catálogos editables desde Hurgo Track.

Quién es dueño de qué:
- ``company``: los crea y edita cada empresa para lo suyo (tipos de producto, unidades, marcas,
  documentos que exige). Hurgo no los crea. ``show_common``: además muestra, solo para leer,
  los registros de Hurgo (``company_id`` nulo), ej. los documentos del proceso de Hurgo.
- ``hurgo``: logística de Hurgo (etiquetas de cargue, flota, documentos del proceso). Con
  ``common_only`` el modelo es compartido y Hurgo solo ve/edita sus registros (``company_id`` nulo).

``fields``: campos editables además de ``name`` -> "text" | "bool" | "choice:valor=Etiqueta,...".
"""

from dataclasses import dataclass, field

STAGES = "choice:order=Pedido,loading=Cargue,delivery=Entrega,return=Devolución,novelty=Novedad"


@dataclass(frozen=True)
class Catalog:
    key: str
    label: str
    model: str  # "app_label.ModelName"
    scope: str  # "company" | "hurgo"
    fields: dict = field(default_factory=dict)
    show_common: bool = False
    common_only: bool = False


CATALOGS = {c.key: c for c in [
    # De cada empresa
    Catalog("type_item", "Tipos de producto", "orders.M_type_item", "company",
            {"uses_stock": "bool", "is_serialized": "bool"}),
    Catalog("unit", "Unidades", "orders.M_unit", "company", {"symbol": "text"}),
    Catalog("brand", "Marcas", "orders.M_brand", "company"),
    Catalog("document_type", "Documentos que exige", "trips.M_trip_type_attach", "company",
            {"stage": STAGES, "is_required": "bool"}, show_common=True),
    # De Hurgo (logística)
    Catalog("process_document_type", "Documentos del proceso", "trips.M_trip_type_attach", "hurgo",
            {"stage": STAGES, "is_required": "bool"}, common_only=True),
    Catalog("loading_tag", "Etiquetas de cargue", "locations.M_loading_tag", "hurgo"),
    Catalog("type_vehicle", "Tipos de vehículo", "fleet.M_type_vehicle", "hurgo"),
    Catalog("brand_vehicle", "Marcas de vehículo", "fleet.M_brand_vehicle", "hurgo"),
    Catalog("bodywork", "Carrocerías", "fleet.M_bodywork", "hurgo", {"official_code": "text"}),
    Catalog("transit", "Organismos de tránsito", "fleet.M_transit", "hurgo", {"official_code": "text"}),
    Catalog("fleet_document_type", "Documentos de flota", "fleet.M_fleet_document_type", "hurgo",
            {"applies_to": "choice:vehicle=Vehículo,driver=Conductor", "is_required": "bool",
             "has_expiration": "bool"}),
]}
