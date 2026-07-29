"""OpenAI-compatible embeddings HTTP endpoint.

Mirrors src/gateway/embeddings-http.ts.
"""

from __future__ import annotations

from typing import Any

async def handle_open_ai_embeddings_http_request(*args: Any, **kwargs: Any) -> Any: ...
