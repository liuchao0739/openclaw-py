"""Gateway shared-auth generation enforcement.

Mirrors src/gateway/server-shared-auth-generation.ts.
"""

from __future__ import annotations

from typing import Any

SharedGatewayAuthClient = Any
SharedGatewaySessionGenerationState = Any

def disconnect_stale_shared_gateway_auth_clients(*args: Any, **kwargs: Any) -> Any: ...
def disconnect_all_shared_gateway_auth_clients(*args: Any, **kwargs: Any) -> Any: ...
def get_required_shared_gateway_session_generation(*args: Any, **kwargs: Any) -> Any: ...
def set_current_shared_gateway_session_generation(*args: Any, **kwargs: Any) -> Any: ...
def enforce_shared_gateway_session_generation_for_config_write(*args: Any, **kwargs: Any) -> Any: ...
