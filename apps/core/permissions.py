"""Permisos y empresas del usuario.

Igual que en arquitecturabase, las acciones se autorizan con permisos de
modelo (``Meta.permissions``), que los workflows validan con el step
``validate.permission``. Los servicios vuelven a validar con ``require_perm``
para que la regla no dependa de cómo se configure el workflow.
"""

from apps.core.exceptions import BusinessPermissionError


def has_perm(user, perm: str) -> bool:
    return bool(user is not None and user.is_authenticated and user.has_perm(perm))


def require_perm(user, perm: str, message: str):
    if not has_perm(user, perm):
        raise BusinessPermissionError(message)


def user_company_ids(user) -> list[int]:
    """Empresas a las que pertenece el usuario (M_user_company activas)."""
    from apps.companies.repository import R_user_company

    if user is None or not user.is_authenticated:
        return []
    return R_user_company().company_ids_for(user)
