"""OpenAI-compatible `/v1/models` HTTP route backed by configured OpenClaw agents.

Mirrors src/gateway/models-http.ts.
"""

from __future__ import annotations

from typing import Any

async def handle_open_ai_models_http_request(*args: Any, **kwargs: Any) -> Any: ...
