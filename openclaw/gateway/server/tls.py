"""Gateway TLS boundary loads listener certificate material from gateway config.

Mirrors src/gateway/server/tls.ts. The actual TLS runtime loader is deferred
(depends on infra/tls/gateway); this provides the type and a stub.
"""

from __future__ import annotations

from typing import Any, Mapping, TypedDict


class GatewayTlsRuntime(TypedDict, total=False):
    cert: str | None
    key: str | None
    ca: str | None


async def load_gateway_tls_runtime(
    cfg: Mapping[str, Any] | None = None,
    log: Mapping[str, Any] | None = None,
) -> GatewayTlsRuntime:
    """Load certificate/key material for the gateway listener from config.

    Stub implementation — returns empty runtime. Real implementation deferred.
    """
    cfg = cfg or {}
    return GatewayTlsRuntime(
        cert=cfg.get("cert"),
        key=cfg.get("key"),
        ca=cfg.get("ca"),
    )
