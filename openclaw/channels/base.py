"""Channel adapter contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class InboundMessage:
    channel_id: str
    sender_id: str
    text: str
    metadata: dict[str, Any] | None = None


@dataclass
class OutboundMessage:
    channel_id: str
    target_id: str
    text: str


class ChannelAdapter(Protocol):
    channel_id: str

    async def send(self, message: OutboundMessage) -> None: ...

    async def receive(self) -> InboundMessage | None: ...
