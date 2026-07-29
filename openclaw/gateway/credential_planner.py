"""Gateway credential planning helpers.

Mirrors src/gateway/credential-planner.ts.
"""

from __future__ import annotations

from typing import Any

trim_to_undefined: Any = None

GatewayCredentialPlan = Any

def trim_credential_to_undefined(*args: Any, **kwargs: Any) -> Any: ...
def has_gateway_token_env_candidate(*args: Any, **kwargs: Any) -> Any: ...
def has_gateway_password_env_candidate(*args: Any, **kwargs: Any) -> Any: ...
def create_gateway_credential_plan(*args: Any, **kwargs: Any) -> Any: ...
