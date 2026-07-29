"""Gateway model catalog cache.

Mirrors src/gateway/server-model-catalog.ts.
"""

from __future__ import annotations

from typing import Any

GatewayModelChoice = Any

def mark_gateway_model_catalog_stale_for_reload(*args: Any, **kwargs: Any) -> Any: ...
async def reset_model_catalog_cache_for_test(*args: Any, **kwargs: Any) -> Any: ...
async def load_gateway_model_catalog(*args: Any, **kwargs: Any) -> Any: ...
