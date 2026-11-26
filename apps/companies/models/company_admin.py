from enginedj.base.models import M_company


class M_company_admin(M_company):
    """Proxy de ``base.M_company`` (no crea tabla): declara los permisos de alta y gestión de empresas.

    - ``create_company``: administración de Hurgo da de alta empresas y su administrador.
    - ``manage_company``: el administrador de una empresa gestiona SU empresa (usuarios, direcciones,
      productos). El alcance lo limita ``user_company_ids(user)`` en cada servicio.
    """

    class Meta:
        proxy = True
        verbose_name = "Empresa (alta y gestión)"
        default_permissions = ()
        permissions = [
            ("create_company", "Puede crear empresas y su usuario administrador"),
            ("manage_company", "Puede gestionar su propia empresa (usuarios, direcciones, productos)"),
        ]
