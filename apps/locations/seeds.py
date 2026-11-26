"""Permisos de empresas (base del motor) y direcciones. Ver ``manage.py seed_workflows``."""

ROLES = {
    # Hurgo: empresas (alta), lugares de cargue y etiquetas. Las direcciones de la empresa las crea ella.
    "administracion": [
        "base.view_m_*", "base.add_m_company", "base.change_m_company",
        "locations.view_m_*", "locations.manage_loading_point", "locations.add_m_loading_tag",
        "locations.change_m_loading_tag",
    ],
    "despacho": ["base.view_m_*", "locations.view_m_*", "locations.manage_loading_point"],
    "comercial": ["base.view_m_company", "locations.view_m_*", "locations.add_m_address", "locations.change_m_address"],
    "admin_empresa": ["base.view_m_company", "locations.view_m_*", "locations.add_m_address",
                      "locations.change_m_address"],
}

WORKFLOWS = {
    # Lugares de cargue: los registra y elige Hurgo al gestionar el pedido
    "locations.loading_points": ["locations.view_m_address"],
    "locations.loading_point.save": ["locations.manage_loading_point"],
    "locations.loading_tags": ["locations.view_m_loading_tag"],
    "locations.lookups": ["locations.view_m_address"],
    # Direcciones de una empresa: administración de Hurgo o el admin de esa empresa
    "locations.addresses": ["locations.view_m_address"],
    "locations.address.save": ["locations.add_m_address"],
    "locations.loading_tag.create": ["locations.manage_loading_point"],
}


def seed(stdout):
    """Departamentos y municipios oficiales (DIVIPOLA del DANE). Solo lectura en el sistema."""
    from apps.locations.divipola import load

    load(stdout)
