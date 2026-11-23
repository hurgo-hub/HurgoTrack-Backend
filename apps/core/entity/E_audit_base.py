from typing import Optional

from enginedj.base.entity.base_entity import BaseEntity as E_base


class E_audit_base(E_base):
    """Entidad base con auditoría (espejo de M_audit_base)."""

    def __init__(
        self,
        create_user_id: Optional[int | dict] = None,
        update_user_id: Optional[int | dict] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.create_user_id = create_user_id or kwargs.get("create_user_id_id")
        self.update_user_id = update_user_id or kwargs.get("update_user_id_id")
