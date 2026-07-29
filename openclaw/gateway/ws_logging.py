"""Runtime control for gateway WebSocket logging verbosity.

Mirrors src/gateway/ws-logging.ts.
"""

from __future__ import annotations

from typing import Any

DEFAULT_WS_SLOW_MS: Any = None

GatewayWsLogStyle = Any

def set_gateway_ws_log_style(*args: Any, **kwargs: Any) -> Any: ...
def get_gateway_ws_log_style(*args: Any, **kwargs: Any) -> Any: ...
