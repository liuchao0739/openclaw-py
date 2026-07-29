"""Gateway startup-time runtime services.

Mirrors src/gateway/server-runtime-startup-services.ts.
"""

from __future__ import annotations

from typing import Any

GatewayChannelManager = Any

def start_gateway_channel_health_monitor(*args: Any, **kwargs: Any) -> Any: ...
def start_gateway_runtime_services(*args: Any, **kwargs: Any) -> Any: ...
