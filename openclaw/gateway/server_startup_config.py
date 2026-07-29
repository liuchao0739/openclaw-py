"""Gateway startup config loads, repairs, validates, and activates runtime config

Mirrors src/gateway/server-startup-config.ts.
"""

from __future__ import annotations

from typing import Any

ActivateRuntimeSecrets = Any
GatewayStartupConfigSnapshotLoadResult = Any

def create_runtime_secrets_activator(*args: Any, **kwargs: Any) -> Any: ...
def assert_valid_gateway_startup_config_snapshot(*args: Any, **kwargs: Any) -> Any: ...
async def load_gateway_startup_config_snapshot(*args: Any, **kwargs: Any) -> Any: ...
async def prepare_gateway_startup_config(*args: Any, **kwargs: Any) -> Any: ...
