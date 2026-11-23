from typing import Optional

from apps.core.entity import E_audit_base


class E_type_item(E_audit_base):

    def __init__(
        self,
        name: Optional[str] = None,
        is_serialized: Optional[bool] = False,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.name = name
        self.is_serialized = is_serialized
