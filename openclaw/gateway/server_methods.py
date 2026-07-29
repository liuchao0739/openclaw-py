"""Gateway method registry aggregator wires core and plugin RPC descriptors to

Mirrors src/gateway/server-methods.ts.
"""

from __future__ import annotations

from typing import Any

core_gateway_handlers: Any = None

async def handle_gateway_request(*args: Any, **kwargs: Any) -> Any: ...
