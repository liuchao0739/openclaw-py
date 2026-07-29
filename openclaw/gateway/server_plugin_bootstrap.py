"""Gateway plugin bootstrap helpers.

Mirrors src/gateway/server-plugin-bootstrap.ts.
"""

from __future__ import annotations

from typing import Any

def prepare_gateway_plugin_load(*args: Any, **kwargs: Any) -> Any: ...
def load_gateway_startup_plugins(*args: Any, **kwargs: Any) -> Any: ...
def reload_deferred_gateway_plugins(*args: Any, **kwargs: Any) -> Any: ...
