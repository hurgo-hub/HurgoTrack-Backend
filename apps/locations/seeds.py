"""Permisos de empresas (base del motor) y direcciones. Ver ``manage.py seed_workflows``."""

ROLES = {
    "administracion": ["base.*", "locations.*"],
    "despacho": ["base.view_m_*", "locations.view_m_*", "locations.manage_loading_point"],
    "comercial": ["base.view_m_company", "locations.view_m_*", "locations.add_m_address", "locations.change_m_address"],
}

WORKFLOWS = {
    "locations.recipients": ["locations.view_m_address"],
    # Lugares de cargue: los registra y elige Hurgo al gestionar el pedido
    "locations.loading_points": ["locations.view_m_address"],
    "locations.loading_point.save": ["locations.manage_loading_point"],
    "locations.loading_tags": ["locations.view_m_loading_tag"],
    "locations.loading_tag.create": ["locations.manage_loading_point"],
}
