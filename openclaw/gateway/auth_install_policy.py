"""Gateway install auth policy used by service/install flows.

Mirrors src/gateway/auth-install-policy.ts.
"""

from __future__ import annotations

from typing import Any

def should_require_gateway_token_for_install(*args: Any, **kwargs: Any) -> Any: ...
