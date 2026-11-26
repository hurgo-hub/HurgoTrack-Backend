"""Permisos y workflows de pedidos (pasos 1 y 2). Ver ``manage.py seed_workflows``."""

ROLES = {
    # Hurgo gestiona el pedido (ver, confirmar, cargue, cancelar); no crea productos, tipos, marcas
    # ni unidades: eso es de cada empresa.
    "administracion": [
        "orders.view_m_*", "orders.confirm_order", "orders.cancel_confirmed_order", "orders.view_all_order",
        "orders.set_loading_point_order",
    ],
    "despacho": [
        "orders.view_m_*",
        "orders.add_m_order", "orders.change_m_order", "orders.submit_order", "orders.cancel_order",
        "orders.confirm_order", "orders.cancel_confirmed_order", "orders.view_all_order",
        "orders.create_any_company_order", "orders.set_loading_point_order",
    ],
    "comercial": [
        "orders.view_m_order", "orders.add_m_order", "orders.change_m_order", "orders.submit_order",
        "orders.cancel_order", "orders.view_m_order_line", "orders.view_m_order_event",
        "orders.view_m_item", "orders.view_m_type_item", "orders.view_m_brand",
    ],
    # Admin de empresa: lo del comercial + su catálogo de productos (solo su empresa)
    "admin_empresa": [
        "orders.view_m_order", "orders.add_m_order", "orders.change_m_order", "orders.submit_order",
        "orders.cancel_order", "orders.view_m_order_line", "orders.view_m_order_event",
        "orders.view_m_item", "orders.add_m_item", "orders.change_m_item", "orders.view_m_type_item",
        "orders.view_m_brand",
    ],
}

# workflow (= step) -> permisos que valida ``validate.permission`` antes del step.
# Los servicios vuelven a validar.
WORKFLOWS = {
    "orders.create": ["orders.add_m_order"],
    "orders.update": ["orders.change_m_order"],
    "orders.submit": ["orders.submit_order"],
    "orders.confirm": ["orders.confirm_order"],
    "orders.cancel": ["orders.view_m_order"],  # el servicio decide entre cancel_order y cancel_confirmed_order
    "orders.retrieve": ["orders.view_m_order"],
    "orders.list": ["orders.view_m_order"],
    "orders.items": ["orders.add_m_order"],
    "orders.pending_lines": ["trips.build_trip"],
    "orders.set_loading_point": ["orders.set_loading_point_order"],
    "orders.company_items": ["orders.view_m_item"],
    "orders.item.save": ["orders.add_m_item"],
    # Documentos del pedido (el servicio valida: usuarios de la empresa del pedido o despacho)
    "orders.documents": ["orders.view_m_order"],
    "orders.attach": ["orders.view_m_order"],
}
