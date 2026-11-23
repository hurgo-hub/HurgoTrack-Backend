from typing import Optional

from enginedj.base.entity import E_model_base


class E_odoo_sync_log(E_model_base):

    def __init__(
        self,
        operation: Optional[str] = None,
        odoo_model: Optional[str] = '',
        reference: Optional[str] = '',
        status: Optional[str] = None,
        request: Optional[dict] = None,
        response: Optional[dict] = None,
        error: Optional[str] = '',
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.operation = operation
        self.odoo_model = odoo_model
        self.reference = reference
        self.status = status
        self.request = request if request is not None else {}
        self.response = response if response is not None else {}
        self.error = error
