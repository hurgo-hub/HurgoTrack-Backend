"""Permisos y workflows de stock y solicitudes de compra. Ver ``manage.py seed_workflows``.

Rol nuevo ``facturador``: usuario de la empresa cliente (ej. Distritodo) que recibe las
solicitudes de compra de Hurgo, compra en Odoo y registra la compra. Ve solo su empresa.
"""

ROLES = {
    "administracion": ["stock.*"],
    "despacho": [
        "stock.view_m_*", "stock.view_all_stock", "stock.view_all_purchase_request",
        "stock.manage_purchase_request", "stock.link_purchase_request",
    ],
    "admin_empresa": [
        "stock.view_m_stock", "stock.view_m_stock_move", "stock.view_m_purchase_request",
        "stock.view_m_purchase_request_line", "stock.link_purchase_request",
    ],
    "facturador": [
        "stock.view_m_stock", "stock.view_m_stock_move", "stock.view_m_purchase_request",
        "stock.view_m_purchase_request_line", "stock.link_purchase_request",
    ],
}

WORKFLOWS = {
    "stock.requirements": ["stock.view_m_stock"],
    "stock.list": ["stock.view_m_stock"],
    "stock.moves": ["stock.view_m_stock_move"],
    "stock.adjust": ["stock.adjust_stock"],
    "stock.purchase_request.create": ["stock.manage_purchase_request"],
    "stock.purchase_request.send": ["stock.manage_purchase_request"],
    "stock.purchase_request.cancel": ["stock.manage_purchase_request"],
    "stock.purchase_request.link_purchase": ["stock.link_purchase_request"],
    "stock.purchase_request.retrieve": ["stock.view_m_purchase_request"],
    "stock.purchase_request.list": ["stock.view_m_purchase_request"],
}
