"""Gateway OpenAI-compatible chat completions endpoint.

Mirrors src/gateway/openai-http.ts.
"""

from __future__ import annotations

from typing import Any

test_only_open_ai_http: Any = None

async def handle_open_ai_http_request(*args: Any, **kwargs: Any) -> Any: ...
