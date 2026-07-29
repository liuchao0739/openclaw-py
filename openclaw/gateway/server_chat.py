"""Gateway chat runtime projects agent events into chat/session subscriber

Mirrors src/gateway/server-chat.ts.
"""

from __future__ import annotations

from typing import Any

ChatEventBroadcast = Any
NodeSendToSession = Any
AgentEventHandlerOptions = Any

def create_agent_event_handler(*args: Any, **kwargs: Any) -> Any: ...
