"""Gateway tool invocation engine.

Mirrors src/gateway/tools-invoke-shared.ts.
"""

from __future__ import annotations

from typing import Any

ToolsInvokeInput = Any

async def invoke_gateway_tool(*args: Any, **kwargs: Any) -> Any: ...
