from typing import Optional

from apps.core.entity import E_audit_base


class E_bodywork(E_audit_base):

    def __init__(
        self,
        name: Optional[str] = None,
        official_code: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.name = name
        self.official_code = official_code
