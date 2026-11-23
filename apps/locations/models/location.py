from django.db import models

from enginedj.base.models import M_model_base


class M_location(M_model_base, models.Model):
    """Departamento o municipio con código DANE. El municipio apunta a su departamento con ``parent_id``."""

    model_name = "location"

    location_type_choices = [
        ("department", "Departamento"),
        ("municipality", "Municipio"),
    ]

    country_id = models.ForeignKey("locations.M_country", on_delete=models.PROTECT, null=False, blank=False,
                                   related_name="location_country_id", db_column="country_id")
    parent_id = models.ForeignKey("locations.M_location", on_delete=models.PROTECT, null=True, blank=True,
                                  related_name="location_parent_id", db_column="parent_id",
                                  help_text="location_id del .mwb: departamento del municipio. Vacío en departamentos.")
    location_type = models.CharField(max_length=15, null=False, blank=False, choices=location_type_choices)
    code_dane = models.CharField(max_length=8, null=False, blank=False, unique=True,
                                 help_text="2 dígitos departamento, 5 municipio.")
    name = models.CharField(max_length=120, null=False, blank=False)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "location"
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(location_type="department", parent_id__isnull=True)
                    | models.Q(location_type="municipality", parent_id__isnull=False)
                ),
                name="ck_location_parent_by_type",
            ),
        ]
