"""Web channel stub backed by in-memory queue."""

from __future__ import annotations

import asyncio
from collections import deque

from openclaw.channels.base import ChannelAdapter, InboundMessage, OutboundMessage


class WebChannel(ChannelAdapter):
    channel_id = "web"

    def __init__(self) -> None:
        self._inbound: deque[InboundMessage] = deque()
        self._outbound: deque[OutboundMessage] = deque()
        self._lock = asyncio.Lock()

    async def enqueue_inbound(self, sender_id: str, text: str) -> None:
        async with self._lock:
            self._inbound.append(
                InboundMessage(channel_id=self.channel_id, sender_id=sender_id, text=text)
            )

    async def send(self, message: OutboundMessage) -> None:
        async with self._lock:
            self._outbound.append(message)

    async def receive(self) -> InboundMessage | None:
        async with self._lock:
            if not self._inbound:
                return None
            return self._inbound.popleft()

    async def drain_outbound(self) -> list[OutboundMessage]:
        async with self._lock:
            items = list(self._outbound)
            self._outbound.clear()
            return items
