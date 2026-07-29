"""HTTP endpoint adapter for invoking gateway tools from OpenAI-compatible clients.

Mirrors src/gateway/tools-invoke-http.ts.
"""

from __future__ import annotations

from typing import Any

async def handle_tools_invoke_http_request(*args: Any, **kwargs: Any) -> Any: ...
