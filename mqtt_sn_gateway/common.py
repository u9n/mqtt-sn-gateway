from __future__ import annotations

from datetime import datetime
from typing import Tuple

from attrs import define

@define
class MqttSnClient:
    client_id: bytes
    keep_alive_to: datetime
    remote_addr: Tuple[str, int]
