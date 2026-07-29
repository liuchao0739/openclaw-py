"""Gateway HTTP server routes control UI, OpenAI-compatible APIs, plugin HTTP

Mirrors src/gateway/server-http.ts.
"""

from __future__ import annotations

from typing import Any

def create_gateway_http_server(*args: Any, **kwargs: Any) -> Any: ...
def attach_gateway_upgrade_handler(*args: Any, **kwargs: Any) -> Any: ...
async def run_gateway_http_request_stages(*args: Any, **kwargs: Any) -> Any: ...
