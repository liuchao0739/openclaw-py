"""Gateway cron runtime service runs scheduled agent turns, heartbeat wakeups,

Mirrors src/gateway/server-cron.ts.
"""

from __future__ import annotations

from typing import Any

GatewayCronState = Any

def build_gateway_cron_service(*args: Any, **kwargs: Any) -> Any: ...
