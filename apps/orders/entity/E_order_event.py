from datetime import datetime
from typing import Optional

from django.utils import timezone

from apps.core.entity import E_audit_base


class E_order_event(E_audit_base):

    def __init__(
        self,
        order_id: Optional[int | dict] = None,
        user_id: Optional[int | dict] = None,
        event_date: Optional[datetime] = None,
        from_state: Optional[str] = '',
        to_state: Optional[str] = '',
        name: Optional[str] = None,
        description: Optional[str] = '',
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.order_id = order_id or kwargs.get("order_id_id")
        self.user_id = user_id or kwargs.get("user_id_id")
        self.event_date = event_date if event_date is not None else timezone.now()
        self.from_state = from_state
        self.to_state = to_state
        self.name = name
        self.description = description
