"""Permisos y workflows de alta y gestión de empresas. Ver ``manage.py seed_workflows``.

Rol nuevo ``admin_empresa``: administrador de UNA empresa cliente. Gestiona sus usuarios
(admin_empresa, comercial, facturador), direcciones y productos, y hace lo de comercial y
facturador. Nunca recibe permisos ``view_all_*`` ni de despacho: todo lo ve limitado a su empresa.
"""

ROLES = {
    # Hurgo crea la empresa con su primer admin y gestiona roles; no administra los usuarios de la empresa
    "administracion": ["companies.create_company", "companies.manage_roles"],
    "admin_empresa": ["companies.manage_company"],
}

WORKFLOWS = {
    "companies.create": ["companies.create_company"],
    "companies.update": ["companies.create_company"],
    "companies.list": ["companies.create_company"],
    "companies.mine": ["companies.manage_company"],
    "companies.users": ["companies.manage_company"],
    "companies.user.save": ["companies.manage_company"],
    # Roles con permisos y usuarios (administración de Hurgo)
    "roles.list": ["companies.manage_roles"],
    "roles.permissions": ["companies.manage_roles"],
    "roles.save": ["companies.manage_roles"],
    "users.list": ["companies.manage_roles"],
    "users.save": ["companies.manage_roles"],
}
