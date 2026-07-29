"""WebSocket runtime adapter wires a built GatewayRequestContext into the lower

Mirrors src/gateway/server-ws-runtime.ts.
"""

from __future__ import annotations

from typing import Any

def attach_gateway_ws_handlers(*args: Any, **kwargs: Any) -> Any: ...
