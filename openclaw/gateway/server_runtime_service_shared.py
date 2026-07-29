"""Shared Gateway runtime service helpers.

Mirrors src/gateway/server-runtime-service-shared.ts.
"""

from __future__ import annotations

from typing import Any

GatewayRuntimeServiceLogger = Any

def create_noop_heartbeat_runner(*args: Any, **kwargs: Any) -> Any: ...
