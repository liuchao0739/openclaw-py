"""Gateway server implementation builds runtime state, method registries, HTTP

Mirrors src/gateway/server.impl.ts.
"""

from __future__ import annotations

from typing import Any

GatewayCloseOptions = Any
GatewayServer = Any
GatewayServerOptions = Any

async def reset_model_catalog_cache_for_test(*args: Any, **kwargs: Any) -> Any: ...
async def start_gateway_server(*args: Any, **kwargs: Any) -> Any: ...
