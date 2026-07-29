"""Lazy public entrypoint for the gateway server implementation.

Mirrors src/gateway/server.ts.
"""

from __future__ import annotations

from typing import Any

async def start_gateway_server(*args: Any, **kwargs: Any) -> Any: ...
async def reset_model_catalog_cache_for_test(*args: Any, **kwargs: Any) -> Any: ...
