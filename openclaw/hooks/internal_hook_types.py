"""Internal hook types define runtime hook event families and payload contracts.

Mirrors src/hooks/internal-hook-types.ts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Literal, Awaitable

InternalHookEventType = Literal["command", "session", "agent", "gateway", "message"]


@dataclass
class InternalHookEvent:
    """Runtime hook event with type, action, session key, context, and messages."""

    type: str
    action: str
    session_key: str
    context: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    messages: list[str] = field(default_factory=list)


InternalHookHandler = Callable[[InternalHookEvent], Awaitable[None] | None]
