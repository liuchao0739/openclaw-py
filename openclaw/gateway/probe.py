"""Gateway reachability probe client.

Mirrors src/gateway/probe.ts.
"""

from __future__ import annotations

from typing import Any

MIN_PROBE_TIMEOUT_MS: Any = None
MAX_TIMER_DELAY_MS: Any = None

GatewayProbeAuth = Any
GatewayProbeClose = Any
GatewayProbeCapability = Any
GatewayProbeAuthSummary = Any
GatewayProbeServerSummary = Any
GatewayProbeResult = Any

def clamp_probe_timeout_ms(*args: Any, **kwargs: Any) -> Any: ...
def is_pairing_pending_probe_failure(*args: Any, **kwargs: Any) -> Any: ...
def resolve_gateway_probe_capability(*args: Any, **kwargs: Any) -> Any: ...
async def probe_gateway(*args: Any, **kwargs: Any) -> Any: ...
