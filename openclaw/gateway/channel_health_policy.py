"""Gateway channel health policy.

Mirrors src/gateway/channel-health-policy.ts.
"""

from __future__ import annotations

from typing import Any

DEFAULT_CHANNEL_STALE_EVENT_THRESHOLD_MS: Any = None
DEFAULT_CHANNEL_CONNECT_GRACE_MS: Any = None

ChannelHealthEvaluation = Any
ChannelHealthPolicy = Any

def evaluate_channel_health(*args: Any, **kwargs: Any) -> Any: ...
def resolve_channel_restart_reason(*args: Any, **kwargs: Any) -> Any: ...
