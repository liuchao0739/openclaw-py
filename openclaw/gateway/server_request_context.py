"""Gateway request context factory.

Mirrors src/gateway/server-request-context.ts.
"""

from __future__ import annotations

from typing import Any

GatewayRequestContextParams = Any

def create_gateway_request_context(*args: Any, **kwargs: Any) -> Any: ...
