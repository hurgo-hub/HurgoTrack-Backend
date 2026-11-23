from typing import Optional

from enginedj.base.entity import E_model_base


class E_brand(E_model_base):

    def __init__(
        self,
        name: Optional[str] = None,
        company_id: Optional[int | dict] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.name = name
        self.company_id = company_id or kwargs.get("company_id_id")
