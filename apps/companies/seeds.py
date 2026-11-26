"""Permisos y workflows de alta y gestión de empresas. Ver ``manage.py seed_workflows``.

Rol nuevo ``admin_empresa``: administrador de UNA empresa cliente. Gestiona sus usuarios
(admin_empresa, comercial, facturador), direcciones y productos, y hace lo de comercial y
facturador. Nunca recibe permisos ``view_all_*`` ni de despacho: todo lo ve limitado a su empresa.
"""

ROLES = {
    "administracion": ["companies.*"],
    "admin_empresa": ["companies.manage_company"],
}

WORKFLOWS = {
    "companies.create": ["companies.create_company"],
    "companies.update": ["companies.create_company"],
    "companies.list": ["companies.create_company"],
    "companies.mine": ["companies.manage_company"],
    "companies.users": ["companies.manage_company"],
    "companies.user.save": ["companies.manage_company"],
}
