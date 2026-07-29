"""Gateway event subscription wiring for agent, heartbeat, transcript, and lifecycle broadcasts.

Mirrors src/gateway/server-runtime-subscriptions.ts.
"""

from __future__ import annotations

from typing import Any

def start_gateway_event_subscriptions(*args: Any, **kwargs: Any) -> Any: ...
