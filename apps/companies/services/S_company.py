"""Alta de empresas (administración de Hurgo) y gestión de cada empresa por su administrador.

- ``create``: Hurgo crea la empresa cliente (la que pide y guarda sus direcciones de entrega) y,
  opcionalmente, su usuario administrador (rol ``admin_empresa``), con la contraseña inicial que
  escribe Hurgo. ``is_freelance`` (conductor sin empresa que acepta solicitudes de cargue) aún no
  se desarrolla: estas empresas siempre son ``is_client``.
- ``users`` / ``save_user``: el admin de la empresa crea y edita los usuarios de SU empresa, solo
  con los roles de alcance empresa (``M_role.scope``). Nunca roles de Hurgo (despacho, administración, conductor).
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction

from enginedj.base.exceptions import BusinessError, BusinessNotFound, BusinessPermissionError
from enginedj.base.models import M_company, M_user_company
from enginedj.base.services.permissions import has_perm, require_perm, user_company_ids

User = get_user_model()

COMPANY_ADMIN_ROLE = "admin_empresa"


def _company_roles() -> list[str]:
    """Roles que se pueden dar a usuarios de una empresa: los de alcance "empresa" (incluye los nuevos)."""
    from apps.companies.services.S_role import company_role_names

    return company_role_names()


def _label(name):
    from apps.companies.services.S_role import role_label

    return role_label(name)
COMPANY_FIELDS = ("name", "document_number", "verification_digit", "email", "phone")


class S_company:

    # ------------------------------------------------------------------
    # Alcance
    # ------------------------------------------------------------------
    @staticmethod
    def require_manage(user, company_id):
        """Solo el administrador de la empresa gestiona lo suyo (Hurgo la crea con su primer admin)."""
        if has_perm(user, "companies.manage_company") and company_id in user_company_ids(user):
            return
        raise BusinessPermissionError("Solo puedes gestionar tu propia empresa.")

    @staticmethod
    def _company(company_id) -> M_company:
        company = M_company.objects.filter(pk=company_id).first()
        if company is None:
            raise BusinessNotFound("La empresa no existe.")
        return company

    # ------------------------------------------------------------------
    # Alta (administración de Hurgo)
    # ------------------------------------------------------------------
    @transaction.atomic
    def create(self, user, *, company: dict, admin: dict | None = None):
        require_perm(user, "companies.create_company", "Solo administración de Hurgo crea empresas.")
        number = (company.get("document_number") or "").strip()
        if M_company.objects.filter(document_number=number).exists():
            raise BusinessError(f"Ya existe una empresa con el NIT {number}.", code="duplicate_company")
        new = M_company.objects.create(
            name=company["name"].strip(), document_type="NIT", document_number=number,
            verification_digit=company.get("verification_digit") or "", email=company.get("email") or "",
            phone=company.get("phone") or "", is_client=True, create_user=user,
        )
        # Su propio esquema de PostgreSQL (aislamiento): ahí van sus catálogos, productos, pedidos...
        from apps.companies.tenancy import create_company_schema

        create_company_schema(new)
        admin_user = None
        if admin:
            admin_user = self._create_user(new, {**admin, "role": COMPANY_ADMIN_ROLE}, user)
        new.admins = [admin_user.username] if admin_user else []  # como en list()
        return new, admin_user

    @transaction.atomic
    def update(self, user, company_id, data: dict):
        require_perm(user, "companies.create_company", "Solo administración de Hurgo edita empresas.")
        company = self._company(company_id)
        if not company.is_client:
            raise BusinessError("La empresa Hurgo se configura en el .env del servidor.", code="not_client")
        number = (data.get("document_number") or company.document_number).strip()
        if M_company.objects.filter(document_number=number).exclude(pk=company.pk).exists():
            raise BusinessError(f"Ya existe una empresa con el NIT {number}.", code="duplicate_company")
        for field in COMPANY_FIELDS:
            if field in data:
                setattr(company, field, data[field] if not isinstance(data[field], str) else data[field].strip())
        if "is_active" in data:
            company.is_active = data["is_active"]
        company.update_user = user
        company.save()
        return company

    def list(self, user):
        require_perm(user, "companies.create_company", "Solo administración de Hurgo ve todas las empresas.")
        # Solo clientes: la empresa Hurgo (transportador) se configura en el .env (ver companies/seeds.py)
        companies = list(M_company.objects.filter(is_client=True).order_by("name"))
        admins = {}
        for link in M_user_company.objects.filter(
            is_active=True, user_id__groups__name=COMPANY_ADMIN_ROLE
        ).select_related("user_id"):
            admins.setdefault(link.company_id_id, []).append(link.user_id.username)
        for company in companies:
            company.admins = sorted(set(admins.get(company.pk, [])))
        return companies

    # ------------------------------------------------------------------
    # Gestión de la propia empresa (admin de empresa)
    # ------------------------------------------------------------------
    def mine(self, user):
        """Empresas que el usuario gestiona y los tipos de producto (para el formulario de productos)."""
        from apps.orders.models import M_type_item

        if not has_perm(user, "companies.manage_company"):
            raise BusinessPermissionError("No administras ninguna empresa.")
        companies = M_company.objects.filter(pk__in=user_company_ids(user), is_active=True).order_by("name")
        types = []
        if companies:  # los tipos viven en el esquema de la empresa
            from apps.companies.tenancy import company_schema

            with company_schema(companies[0].pk):
                types = list(M_type_item.objects.filter(is_active=True).order_by("name"))
        return {
            "companies": [{"id": c.id, "name": c.name, "is_client": c.is_client} for c in companies],
            "type_items": [{"id": t.id, "name": t.name, "uses_stock": t.uses_stock} for t in types],
            "roles": [{"value": r, "label": _label(r)} for r in _company_roles()],
        }

    def users(self, user, company_id):
        self.require_manage(user, company_id)
        self._company(company_id)
        links = (
            M_user_company.objects.filter(company_id=company_id, is_active=True)
            .select_related("user_id")
            .prefetch_related("user_id__groups")
            .order_by("user_id__username")
        )
        return [self._user_row(link.user_id) for link in links]

    @staticmethod
    def _user_row(u):
        company_roles = _company_roles()
        roles = [g.name for g in u.groups.all() if g.name in company_roles]
        return {"id": u.id, "username": u.username, "first_name": u.first_name, "last_name": u.last_name,
                "email": u.email, "is_active": u.is_active, "role": roles[0] if roles else None,
                "role_label": _label(roles[0]) if roles else None}

    @transaction.atomic
    def save_user(self, user, company_id, data: dict):
        """Crea (sin user_id) o edita un usuario de la empresa."""
        self.require_manage(user, company_id)
        company = self._company(company_id)
        company_roles = _company_roles()
        if data.get("role") not in company_roles:
            raise BusinessError("Rol no permitido para usuarios de una empresa.", code="invalid_role")
        if not data.get("user_id"):
            return self._user_row(self._create_user(company, data, user))

        target = User.objects.select_for_update().filter(pk=data["user_id"]).first()
        if target is None or not M_user_company.objects.filter(user_id=target, company_id=company).exists():
            raise BusinessNotFound("El usuario no pertenece a esta empresa.")
        if target.is_staff or target.is_superuser or target.groups.exclude(name__in=company_roles).exists():
            raise BusinessPermissionError("Ese usuario lo administra Hurgo.")
        if target.pk == user.pk and (data["role"] != COMPANY_ADMIN_ROLE or data.get("is_active") is False):
            raise BusinessError("No puedes quitarte el rol de administrador ni desactivarte.", code="self_demote")
        for field in ("first_name", "last_name", "email"):
            if field in data:
                setattr(target, field, (data[field] or "").strip())
        if "is_active" in data:
            target.is_active = data["is_active"]
        if data.get("password"):
            self._check_password(data["password"], target)
            target.set_password(data["password"])
        target.save()
        self._set_role(target, data["role"])
        return self._user_row(target)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _create_user(self, company, data: dict, by_user):
        username = (data.get("username") or "").strip()
        if not username:
            raise BusinessError("Indica el usuario.")
        if User.objects.filter(username__iexact=username).exists():
            raise BusinessError(f"El usuario '{username}' ya existe.", code="duplicate_user")
        if not data.get("password"):
            raise BusinessError("Indica la contraseña inicial.", code="password_required")
        new = User(username=username, first_name=(data.get("first_name") or "").strip(),
                   last_name=(data.get("last_name") or "").strip(), email=(data.get("email") or "").strip())
        self._check_password(data["password"], new)
        new.set_password(data["password"])
        new.save()
        M_user_company.objects.create(user_id=new, company_id=company, create_user=by_user)
        self._set_role(new, data["role"])
        return new

    @staticmethod
    def _check_password(password, user):
        try:
            validate_password(password, user=user)
        except ValidationError as exc:
            raise BusinessError(" ".join(exc.messages), code="weak_password")

    @staticmethod
    def _set_role(target, role):
        group = Group.objects.filter(name=role).first()
        if group is None:
            raise BusinessError(f"El rol '{role}' no existe; corre seed_workflows.", code="missing_role")
        target.groups.remove(*Group.objects.filter(name__in=_company_roles()))
        target.groups.add(group)
