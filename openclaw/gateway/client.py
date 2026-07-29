"""OpenClaw Gateway client facade.

Mirrors src/gateway/client.ts.
"""

from __future__ import annotations

from typing import Any

GATEWAY_CLOSE_CODE_HINTS: Any = None
gateway_client_request_error: Any = None

DeviceAuthTokenRecord = Any
GatewayClientHostDeps = Any
GatewayClientRequestOptions = Any
GatewayReconnectPausedInfo = Any
GatewayClientCloseInfo = Any
GatewayClientRequestError = Any
GatewayClientOptions = Any
GatewayClientConnectionMetadata = Any

class GatewayClient: ...

def describe_gateway_close_code(*args: Any, **kwargs: Any) -> Any: ...
def is_gateway_connect_assembly_error(*args: Any, **kwargs: Any) -> Any: ...
def resolve_gateway_client_connect_challenge_timeout_ms(*args: Any, **kwargs: Any) -> Any: ...
