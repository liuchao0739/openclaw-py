"""Gateway secret-input path helpers.

Mirrors src/gateway/secret-input-paths.ts.
"""

from __future__ import annotations

from typing import Any

ALL_GATEWAY_SECRET_INPUT_PATHS: Any = None

SupportedGatewaySecretInputPath = Any

def is_supported_gateway_secret_input_path(*args: Any, **kwargs: Any) -> Any: ...
def read_gateway_secret_input_value(*args: Any, **kwargs: Any) -> Any: ...
def assign_resolved_gateway_secret_input(*args: Any, **kwargs: Any) -> Any: ...
def is_token_gateway_secret_input_path(*args: Any, **kwargs: Any) -> Any: ...
