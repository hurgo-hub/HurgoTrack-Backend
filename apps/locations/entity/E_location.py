from typing import Optional

from apps.core.entity import E_audit_base


class E_location(E_audit_base):

    def __init__(
        self,
        country_id: Optional[int | dict] = None,
        parent_id: Optional[int | dict] = None,
        location_type: Optional[str] = None,
        code_dane: Optional[str] = None,
        name: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.country_id = country_id or kwargs.get("country_id_id")
        self.parent_id = parent_id or kwargs.get("parent_id_id")
        self.location_type = location_type
        self.code_dane = code_dane
        self.name = name
