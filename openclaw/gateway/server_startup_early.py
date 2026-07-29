"""Gateway early-startup runtime helpers.

Mirrors src/gateway/server-startup-early.ts.
"""

from __future__ import annotations

from typing import Any

async def start_gateway_plugin_discovery(*args: Any, **kwargs: Any) -> Any: ...
async def start_gateway_early_runtime(*args: Any, **kwargs: Any) -> Any: ...
