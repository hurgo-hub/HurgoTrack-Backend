"""Odoo simulado (``ODOO_SIMULATED=True``): responde como el JSON-RPC de Odoo, sin red.

Sirve para probar el flujo completo sin un Odoo real. Las compras las crea el botón "Simular compra
en Odoo" (``S_odoo_simulator``) y quedan en la copia local (``odoo_purchase``) marcadas con
``raw.simulated``; este repositorio las devuelve como lo haría Odoo, así el resto del sistema
(registrar la compra, sumar al stock, notificar la entrega) no se entera de que es simulado.
"""

from datetime import timezone as dt_timezone


def _where(domain, field):
    for cond in domain or []:
        if isinstance(cond, (list, tuple)) and len(cond) == 3 and cond[0] == field and cond[1] == "=":
            return cond[2]
    return None


def _purchase(p):
    date_order = p.date_order.astimezone(dt_timezone.utc).strftime("%Y-%m-%d %H:%M:%S") if p.date_order else False
    return {
        "id": p.odoo_id, "name": p.name, "state": p.state, "partner_id": [p.partner_odoo_id, p.partner_name],
        "date_order": date_order, "amount_total": float(p.amount_total or 0),
        "order_line": [line.odoo_line_id for line in p.odoo_purchase_line_purchase_id.all().order_by("odoo_line_id")],
        "simulated": True,
    }


def _line(line, purchase):
    return {
        "id": line.odoo_line_id, "order_id": [purchase.odoo_id, purchase.name],
        "product_id": [line.product_odoo_id, line.product_name] if line.product_odoo_id else False,
        "name": line.product_name, "product_qty": float(line.product_qty), "qty_received": float(line.qty_received),
        "product_uom": [None, line.uom_name] if line.uom_name else False, "simulated": True,
    }


class SimulatedOdooRepository:
    """Misma interfaz que ``ApiOdooRepository`` (search_read, execute_kw, message_post)."""

    def __init__(self, force_cache: bool = False):
        pass

    @staticmethod
    def _simulated():
        from apps.apiOdoo.models import M_odoo_purchase

        return M_odoo_purchase.objects.filter(raw__simulated=True, is_active=True)

    def search_read(self, model, domain, fields, limit=None, order=None):
        if model == "purchase.order":
            qs = self._simulated()
            name, odoo_id = _where(domain, "name"), _where(domain, "id")
            if name is not None:
                qs = qs.filter(name=name)
            if odoo_id is not None:
                qs = qs.filter(odoo_id=odoo_id)
            rows = [_purchase(p) for p in qs.order_by("odoo_id")]
        elif model == "purchase.order.line":
            purchase = self._simulated().filter(odoo_id=_where(domain, "order_id")).first()
            rows = [_line(line, purchase) for line in
                    purchase.odoo_purchase_line_purchase_id.all().order_by("odoo_line_id")] if purchase else []
        else:  # contactos y productos: el simulador no tiene catálogo propio
            rows = []
        return rows[:limit] if limit else rows

    def execute_kw(self, model, method, args, kwargs=None):
        if method == "search_read":
            kwargs = kwargs or {}
            return self.search_read(model, args[0] if args else [], kwargs.get("fields"), kwargs.get("limit"),
                                    kwargs.get("order"))
        return []

    def message_post(self, model, res_id, body):
        return 1  # Odoo devuelve el id del mensaje del chatter
