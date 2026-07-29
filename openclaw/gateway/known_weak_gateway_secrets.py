"""Gateway known-weak credential guard.

Mirrors src/gateway/known-weak-gateway-secrets.ts.
"""

from __future__ import annotations

from typing import Any

KNOWN_WEAK_GATEWAY_TOKEN_PLACEHOLDERS: Any = None
KNOWN_WEAK_GATEWAY_PASSWORD_PLACEHOLDERS: Any = None

def assert_gateway_auth_not_known_weak(*args: Any, **kwargs: Any) -> Any: ...
