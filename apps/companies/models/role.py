from django.db import models

from enginedj.base.models import M_model_base


class M_role(M_model_base, models.Model):
    """Datos de un rol (``auth.Group``): alcance, descripción y si es de sistema.

    - ``scope="company"``: lo puede asignar el administrador de una empresa a sus usuarios. Solo
      puede llevar permisos de la lista permitida (los de comercial, facturador y admin de empresa).
    - ``scope="hurgo"``: roles del equipo de Hurgo (despacho, administración, conductor...).
    - ``is_system``: lo crea ``seed_workflows`` desde los ``seeds.py``; se ve pero no se edita
      (el seed le reescribe los permisos en cada corrida).
    """

    model_name = "role"

    scope_choices = [("hurgo", "Hurgo"), ("company", "Empresa")]

    group = models.OneToOneField("auth.Group", on_delete=models.CASCADE, related_name="role", db_column="group_id")
    scope = models.CharField(max_length=10, null=False, blank=False, choices=scope_choices, default="hurgo")
    label = models.CharField(max_length=150, null=False, blank=True, default="", help_text="Nombre visible.")
    description = models.TextField(null=False, blank=True, default="")
    is_system = models.BooleanField(default=False)

    def __str__(self):
        return self.label or self.group.name

    class Meta:
        db_table = "role"
        ordering = ["scope", "group__name"]
