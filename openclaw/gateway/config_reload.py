"""Gateway config hot-reload watcher.

Mirrors src/gateway/config-reload.ts.
"""

from __future__ import annotations

from typing import Any

GatewayHotReloadStatus = Any

def start_gateway_config_reloader(*args: Any, **kwargs: Any) -> Any: ...
