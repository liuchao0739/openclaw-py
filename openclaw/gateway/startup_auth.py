"""Gateway startup auth preparation.

Mirrors src/gateway/startup-auth.ts.
"""

from __future__ import annotations

from typing import Any

def merge_gateway_auth_config(*args: Any, **kwargs: Any) -> Any: ...
def merge_gateway_tailscale_config(*args: Any, **kwargs: Any) -> Any: ...
async def ensure_gateway_startup_auth(*args: Any, **kwargs: Any) -> Any: ...
