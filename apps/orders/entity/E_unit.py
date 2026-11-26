from typing import Optional

from enginedj.base.entity import E_model_base


class E_unit(E_model_base):

    def __init__(self, symbol: Optional[str] = None, name: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.symbol = symbol
        self.name = name
