from typing import Optional

from enginedj.base.entity import E_model_base


class E_type_item(E_model_base):

    def __init__(
        self,
        name: Optional[str] = None,
        is_serialized: Optional[bool] = False,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.name = name
        self.is_serialized = is_serialized
