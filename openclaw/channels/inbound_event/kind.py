"""High-level inbound event class for separating actionable user requests from room activity."""

from __future__ import annotations

from typing import Literal

InboundEventKind = Literal["user_request", "room_event"]
