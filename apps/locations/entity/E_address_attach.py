from typing import Optional

from enginedj.base.entity import E_model_base


class E_address_attach(E_model_base):

    def __init__(
        self,
        address_id: Optional[int | dict] = None,
        name: Optional[str] = '',
        file: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.address_id = address_id or kwargs.get("address_id_id")
        self.name = name
        self.file = file
