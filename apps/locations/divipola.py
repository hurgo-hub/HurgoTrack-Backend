"""Carga de la DIVIPOLA del DANE (departamentos y municipios de Colombia) desde ``data/divipola.csv``.

Fuente: datos.gov.co, conjunto "DIVIPOLA - Códigos municipios" (DANE). Son datos oficiales de
solo lectura: nadie los crea ni los edita en Hurgo Track; ``seed_workflows`` los carga o
actualiza por ``code_dane`` (idempotente).
"""

import csv
from pathlib import Path

CSV_PATH = Path(__file__).resolve().parent / "data" / "divipola.csv"
LOWER_WORDS = {"de", "del", "la", "las", "los", "y", "e", "el", "en"}


def display_name(name: str) -> str:
    """'SAN SEBASTIÁN DE BUENAVISTA' -> 'San Sebastián de Buenavista'; 'BOGOTÁ, D.C.' -> 'Bogotá, D.C.'."""
    words = []
    for i, word in enumerate(name.strip().split()):
        lower = word.lower()
        if "." in word:
            words.append(word.upper())
        elif i > 0 and lower in LOWER_WORDS:
            words.append(lower)
        else:
            words.append("-".join(part[:1].upper() + part[1:] for part in lower.split("-")))
    return " ".join(words)


def load(stdout=None) -> dict:
    from apps.locations.models import M_country, M_location

    rows = list(csv.DictReader(CSV_PATH.open(encoding="utf-8")))
    country, _ = M_country.objects.get_or_create(iso_code="CO", defaults={"name": "Colombia"})

    existing = {loc.code_dane: loc for loc in M_location.objects.filter(country_id=country)}
    created = updated = 0

    def upsert(code, name, location_type, parent=None):
        nonlocal created, updated
        loc = existing.get(code)
        if loc is None:
            loc = M_location.objects.create(country_id=country, code_dane=code, name=name,
                                            location_type=location_type, parent_id=parent)
            existing[code] = loc
            created += 1
        elif (loc.name, loc.location_type, loc.parent_id_id, loc.is_active) != (
                name, location_type, parent.pk if parent else None, True):
            loc.name, loc.location_type, loc.parent_id, loc.is_active = name, location_type, parent, True
            loc.save()
            updated += 1
        return loc

    dept_rows = {}
    for row in rows:
        dept_rows.setdefault(row["cod_dpto"].strip(), display_name(row["dpto"]))

    if not existing:
        # Primera carga: en bloque (2 inserciones en lugar de ~1.150)
        M_location.objects.bulk_create([
            M_location(country_id=country, code_dane=code, name=name, location_type="department")
            for code, name in dept_rows.items()
        ])
        departments = {d.code_dane: d for d in M_location.objects.filter(country_id=country)}
        M_location.objects.bulk_create([
            M_location(country_id=country, code_dane=row["cod_mpio"].strip(), name=display_name(row["nom_mpio"]),
                       location_type="municipality", parent_id=departments[row["cod_dpto"].strip()])
            for row in rows
        ])
        created = len(dept_rows) + len(rows)
    else:
        departments = {code: upsert(code, name, "department") for code, name in dept_rows.items()}
        for row in rows:
            upsert(row["cod_mpio"].strip(), display_name(row["nom_mpio"]), "municipality",
                   departments[row["cod_dpto"].strip()])

    summary = {"departments": len(departments), "municipalities": len(rows), "created": created, "updated": updated}
    if stdout is not None:
        stdout.write(f"DIVIPOLA: {summary['departments']} departamentos, {summary['municipalities']} municipios "
                     f"({created} nuevos, {updated} actualizados)")
    return summary
