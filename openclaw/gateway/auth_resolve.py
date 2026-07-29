"""Gateway auth resolver.

Mirrors src/gateway/auth-resolve.ts.
"""

from __future__ import annotations

from typing import Any

ResolvedGatewayAuthMode = Any
ResolvedGatewayAuthModeSource = Any
ResolvedGatewayAuth = Any
EffectiveSharedGatewayAuth = Any

def resolve_gateway_auth(*args: Any, **kwargs: Any) -> Any: ...
def resolve_effective_shared_gateway_auth(*args: Any, **kwargs: Any) -> Any: ...
