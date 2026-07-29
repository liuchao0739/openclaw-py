"""Gateway auth token resolution applies explicit/config/SecretRef/env

Mirrors src/gateway/auth-token-resolution.ts.
"""

from __future__ import annotations

from typing import Any

async def resolve_gateway_auth_token(*args: Any, **kwargs: Any) -> Any: ...
