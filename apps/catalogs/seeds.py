"""Permisos y workflows de catálogos. Ver ``manage.py seed_workflows``."""

ROLES = {
    # Hurgo solo gestiona los de logística; tipos, unidades, marcas y documentos son de cada empresa
    "administracion": ["catalogs.manage_hurgo_catalogs"],
    "admin_empresa": ["catalogs.manage_company_catalogs"],
}

# El servicio decide qué catálogo puede ver/editar cada uno (empresa o Hurgo);
# aquí basta con un permiso que tienen ambos roles.
WORKFLOWS = {
    "catalogs.available": ["orders.view_m_type_item"],
    "catalogs.list": ["orders.view_m_type_item"],
    "catalogs.save": ["orders.view_m_type_item"],
}
