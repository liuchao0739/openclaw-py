"""Gateway shutdown and restart close orchestration.

Mirrors src/gateway/server-close.ts.
"""

from __future__ import annotations

from typing import Any

ShutdownResult = Any

def create_gateway_close_handler(*args: Any, **kwargs: Any) -> Any: ...
async def run_gateway_close_prelude(*args: Any, **kwargs: Any) -> Any: ...
