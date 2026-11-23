from typing import Optional

from enginedj.base.entity import E_model_base


class E_transit(E_model_base):

    def __init__(
        self,
        name: Optional[str] = None,
        official_code: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.name = name
        self.official_code = official_code
