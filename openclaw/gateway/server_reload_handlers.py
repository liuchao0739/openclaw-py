"""Gateway hot-reload handlers.

Mirrors src/gateway/server-reload-handlers.ts.
"""

from __future__ import annotations

from typing import Any

GatewayPluginReloadResult = Any

def create_gateway_reload_handlers(*args: Any, **kwargs: Any) -> Any: ...
def start_managed_gateway_config_reloader(*args: Any, **kwargs: Any) -> Any: ...
