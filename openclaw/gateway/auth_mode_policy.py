"""Gateway auth mode policy rejects ambiguous token+password config before

Mirrors src/gateway/auth-mode-policy.ts.
"""

from __future__ import annotations

from typing import Any

EXPLICIT_GATEWAY_AUTH_MODE_REQUIRED_ERROR: Any = None

def has_ambiguous_gateway_auth_mode_config(*args: Any, **kwargs: Any) -> Any: ...
def assert_explicit_gateway_auth_mode_when_both_configured(*args: Any, **kwargs: Any) -> Any: ...
