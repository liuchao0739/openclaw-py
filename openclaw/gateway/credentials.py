"""Gateway credential resolution.

Mirrors src/gateway/credentials.ts.
"""

from __future__ import annotations

from typing import Any

ExplicitGatewayAuth = Any
GatewayCredentialMode = Any
GatewayCredentialPrecedence = Any
GatewayRemoteCredentialPrecedence = Any
GatewayRemoteCredentialFallback = Any

class GatewaySecretRefUnavailableError: ...

def is_gateway_secret_ref_unavailable_error(*args: Any, **kwargs: Any) -> Any: ...
def resolve_gateway_credentials_from_values(*args: Any, **kwargs: Any) -> Any: ...
def resolve_gateway_credentials_from_config(*args: Any, **kwargs: Any) -> Any: ...
def resolve_gateway_probe_credentials_from_config(*args: Any, **kwargs: Any) -> Any: ...
