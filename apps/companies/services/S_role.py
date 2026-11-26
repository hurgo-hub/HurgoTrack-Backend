"""Roles con permisos (``auth.Group`` + ``M_role``) y usuarios de Hurgo.

- Los roles de los ``seeds.py`` se registran como ``is_system`` (solo lectura).
- Los roles de empresa solo pueden llevar permisos de ``company_allowed_permissions()``: la unión
  de los que tienen hoy admin_empresa, comercial y facturador. Así un rol de empresa nunca puede
  ver todas las empresas ni hacer tareas de despacho.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.db import transaction

from enginedj.base.exceptions import BusinessError, BusinessNotFound, BusinessPermissionError
from enginedj.base.services.permissions import require_perm

from apps.companies.models import M_role

User = get_user_model()

SYSTEM_COMPANY_ROLES = {"admin_empresa": "Administrador de la empresa", "comercial": "Comercial",
                        "facturador": "Facturador"}
SYSTEM_LABELS = {"administracion": "Administración", "despacho": "Despacho", "conductor": "Conductor",
                 **SYSTEM_COMPANY_ROLES}
MANAGE_PERM = "companies.manage_roles"
# Módulos cuyos permisos se pueden asignar desde la pantalla de roles
PERMISSION_APPS = ["orders", "trips", "stock", "locations", "fleet", "drivers", "companies", "catalogs", "apiOdoo",
                   "apiSatrack", "base"]


def system_role_names() -> set[str]:
    from enginedj.workflows.management.commands.seed_workflows import seed_modules

    names = set()
    for _, module in seed_modules():
        names |= set(getattr(module, "ROLES", {}).keys())
    return names


def sync_system_roles():
    """Crea el ``M_role`` de cada grupo que falte. Los de los seeds quedan como de sistema."""
    system = system_role_names()
    for group in Group.objects.filter(role__isnull=True):
        M_role.objects.create(
            group=group, is_system=group.name in system, label=SYSTEM_LABELS.get(group.name, group.name),
            scope="company" if group.name in SYSTEM_COMPANY_ROLES else "hurgo",
        )


def company_role_names() -> list[str]:
    sync_system_roles()
    return list(M_role.objects.filter(scope="company", is_active=True).values_list("group__name", flat=True))


def role_label(name: str) -> str:
    role = M_role.objects.filter(group__name=name).first()
    return (role.label if role and role.label else SYSTEM_LABELS.get(name, name))


def company_allowed_permissions():
    return Permission.objects.filter(group__name__in=SYSTEM_COMPANY_ROLES.keys()).distinct()


def perm_code(p: Permission) -> str:
    return f"{p.content_type.app_label}.{p.codename}"


class S_role:

    # ------------------------------------------------------------------
    # Roles
    # ------------------------------------------------------------------
    def list(self, user):
        require_perm(user, MANAGE_PERM, "Solo administración gestiona roles.")
        sync_system_roles()
        roles = M_role.objects.select_related("group").prefetch_related("group__permissions__content_type")
        return [self._row(r) for r in roles.order_by("scope", "group__name")]

    @staticmethod
    def _row(role):
        return {
            "id": role.pk, "name": role.group.name, "label": role.label or role.group.name, "scope": role.scope,
            "description": role.description, "is_system": role.is_system, "is_active": role.is_active,
            "permissions": sorted(perm_code(p) for p in role.group.permissions.all()),
            "users": role.group.user_set.count(),
        }

    def permissions(self, user):
        """Permisos asignables, agrupados por módulo; ``company_allowed`` marca los válidos en roles de empresa."""
        require_perm(user, MANAGE_PERM, "Solo administración gestiona roles.")
        allowed = set(company_allowed_permissions().values_list("pk", flat=True))
        groups = {}
        for p in Permission.objects.filter(content_type__app_label__in=PERMISSION_APPS).select_related(
                "content_type").order_by("content_type__app_label", "name"):
            groups.setdefault(p.content_type.app_label, []).append(
                {"code": perm_code(p), "name": p.name, "company_allowed": p.pk in allowed})
        return [{"app": app, "permissions": perms} for app, perms in groups.items()]

    @transaction.atomic
    def save(self, user, data: dict):
        """Crea (sin id) o edita un rol no de sistema con sus permisos."""
        require_perm(user, MANAGE_PERM, "Solo administración gestiona roles.")
        sync_system_roles()
        scope = data.get("scope") or "hurgo"
        if scope not in ("hurgo", "company"):
            raise BusinessError("Alcance inválido.")
        name = (data.get("name") or "").strip().lower().replace(" ", "_")
        if data.get("id"):
            role = M_role.objects.select_for_update().select_related("group").filter(pk=data["id"]).first()
            if role is None:
                raise BusinessNotFound("El rol no existe.")
            if role.is_system:
                raise BusinessPermissionError("Los roles de sistema no se editan (los define el seed).")
            if name and name != role.group.name:
                if Group.objects.filter(name=name).exclude(pk=role.group_id).exists():
                    raise BusinessError(f"Ya existe el rol '{name}'.", code="duplicate_role")
                role.group.name = name
                role.group.save()
        else:
            if not name:
                raise BusinessError("Indica el nombre del rol.")
            if Group.objects.filter(name=name).exists():
                raise BusinessError(f"Ya existe el rol '{name}'.", code="duplicate_role")
            role = M_role(group=Group.objects.create(name=name), create_user=user)
        role.scope = scope
        role.label = (data.get("label") or "").strip() or role.group.name
        role.description = (data.get("description") or "").strip()
        if "is_active" in data:
            role.is_active = bool(data["is_active"])
        role.update_user = user
        role.save()

        if "permissions" in data:
            codes = set(data["permissions"])
            perms = [p for p in Permission.objects.filter(content_type__app_label__in=PERMISSION_APPS)
                     .select_related("content_type") if perm_code(p) in codes]
            missing = codes - {perm_code(p) for p in perms}
            if missing:
                raise BusinessNotFound(f"Permisos inexistentes: {sorted(missing)}.")
            if scope == "company":
                allowed = set(company_allowed_permissions().values_list("pk", flat=True))
                denied = sorted(perm_code(p) for p in perms if p.pk not in allowed)
                if denied:
                    raise BusinessError(
                        "Un rol de empresa no puede llevar permisos de Hurgo: " + ", ".join(denied),
                        code="permission_not_allowed")
            role.group.permissions.set(perms)
        return self._row(M_role.objects.select_related("group").get(pk=role.pk))

    # ------------------------------------------------------------------
    # Usuarios de Hurgo (despacho, conductores, administración). Los de cada empresa los
    # gestiona su administrador (companies.user.save), no Hurgo.
    # ------------------------------------------------------------------
    @staticmethod
    def _hurgo_users():
        from enginedj.base.models import M_user_company

        company_users = M_user_company.objects.filter(is_active=True).values_list("user_id", flat=True)
        return User.objects.exclude(pk__in=company_users)

    def users(self, user):
        require_perm(user, MANAGE_PERM, "Solo administración gestiona usuarios.")
        return [
            {"id": u.id, "username": u.username, "first_name": u.first_name, "last_name": u.last_name,
             "email": u.email, "is_active": u.is_active, "is_superuser": u.is_superuser,
             "roles": [g.name for g in u.groups.all()]}
            for u in self._hurgo_users().prefetch_related("groups").order_by("username")
        ]

    @transaction.atomic
    def save_user(self, user, data: dict):
        """Crea (sin user_id) o edita un usuario de Hurgo y le asigna roles de Hurgo."""
        require_perm(user, MANAGE_PERM, "Solo administración gestiona usuarios.")
        from apps.companies.services.S_company import S_company

        sync_system_roles()
        roles = list(Group.objects.filter(name__in=data.get("roles") or [], role__is_active=True,
                                          role__scope="hurgo"))
        if len(roles) != len(set(data.get("roles") or [])):
            raise BusinessNotFound("Algún rol no existe, está inactivo o es de empresa (lo asigna la empresa).")
        if data.get("user_id"):
            target = self._hurgo_users().select_for_update().filter(pk=data["user_id"]).first()
            if target is None:
                raise BusinessNotFound("El usuario no existe o es de una empresa (lo gestiona su administrador).")
            if target.pk == user.pk and data.get("is_active") is False:
                raise BusinessError("No puedes desactivarte a ti mismo.", code="self_demote")
        else:
            username = (data.get("username") or "").strip()
            if not username or not data.get("password"):
                raise BusinessError("Indica usuario y contraseña.")
            if User.objects.filter(username__iexact=username).exists():
                raise BusinessError(f"El usuario '{username}' ya existe.", code="duplicate_user")
            target = User(username=username)
        for field in ("first_name", "last_name", "email"):
            if field in data:
                setattr(target, field, (data[field] or "").strip())
        if "is_active" in data:
            target.is_active = bool(data["is_active"])
        if data.get("password"):
            S_company._check_password(data["password"], target)
            target.set_password(data["password"])
        target.save()
        if "roles" in data:
            target.groups.set(roles)
        return next(u for u in self.users(user) if u["id"] == target.pk)
