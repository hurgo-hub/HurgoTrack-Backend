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


def seed(stdout):
    """Empresa Hurgo (transportador, dueña de la flota), con el nombre y el NIT del .env.

    Es una sola y vive en el esquema central: no es cliente, no tiene esquema propio ni hace pedidos.
    """
    from django.conf import settings
    from django.core.management.base import CommandError

    from enginedj.base.models import M_company

    name = (settings.HURGO_COMPANY_NAME or "").strip()
    nit = (settings.HURGO_COMPANY_NIT or "").strip()
    if not (name and nit):
        if not M_company.objects.filter(is_carrier=True, is_freelance=False).exists():
            stdout.write("Empresa Hurgo: falta HURGO_COMPANY_NAME y HURGO_COMPANY_NIT en el .env "
                         "(la flota necesita su empresa).")
        return
    company = M_company.objects.filter(document_number=nit).first()
    if company is not None and company.is_client:
        raise CommandError(f"El NIT {nit} (HURGO_COMPANY_NIT) es de una empresa cliente: {company.name}.")
    if company is None:
        M_company.objects.create(name=name, document_type="NIT", document_number=nit,
                                 verification_digit=settings.HURGO_COMPANY_DV or "", is_carrier=True)
        stdout.write(f"Empresa Hurgo creada: {name} (NIT {nit}).")
        return
    changed = {"name": name, "verification_digit": settings.HURGO_COMPANY_DV or company.verification_digit,
               "is_carrier": True, "is_active": True}
    if any(getattr(company, k) != v for k, v in changed.items()):
        for k, v in changed.items():
            setattr(company, k, v)
        company.save()
