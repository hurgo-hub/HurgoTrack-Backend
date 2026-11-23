from typing import Optional

from enginedj.base.entity import E_model_base


class E_country(E_model_base):

    def __init__(
        self,
        iso_code: Optional[str] = None,
        name: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.iso_code = iso_code
        self.name = name
