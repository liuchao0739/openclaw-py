"""Gateway HTTP/WebSocket runtime state factory.

Mirrors src/gateway/server-runtime-state.ts.
"""

from __future__ import annotations

from typing import Any

async def create_gateway_runtime_state(*args: Any, **kwargs: Any) -> Any: ...
