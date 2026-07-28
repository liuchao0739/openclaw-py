"""Gateway bind URL helpers compute listener URLs from host and port settings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class GatewayBindUrlResult:
    url: str | None = None
    source: str | None = None
    error: str | None = None


def resolve_gateway_bind_url(
    bind: str | None = None,
    custom_bind_host: str | None = None,
    scheme: str = "ws",
    port: int = 0,
    pick_tailnet_host: Callable[[], str | None] | None = None,
    pick_lan_host: Callable[[], str | None] | None = None,
) -> GatewayBindUrlResult | None:
    if bind is None:
        bind = "loopback"
    if bind == "custom":
        host = custom_bind_host.strip() if isinstance(custom_bind_host, str) else None
        if host:
            return GatewayBindUrlResult(
                url=f"{scheme}://{host}:{port}",
                source="gateway.bind=custom",
            )
        return GatewayBindUrlResult(
            error="gateway.bind=custom requires gateway.customBindHost.",
        )
    if bind == "tailnet":
        host = pick_tailnet_host() if pick_tailnet_host else None
        if host:
            return GatewayBindUrlResult(
                url=f"{scheme}://{host}:{port}",
                source="gateway.bind=tailnet",
            )
        return GatewayBindUrlResult(
            error="gateway.bind=tailnet set, but no tailnet IP was found.",
        )
    if bind == "lan":
        host = pick_lan_host() if pick_lan_host else None
        if host:
            return GatewayBindUrlResult(
                url=f"{scheme}://{host}:{port}",
                source="gateway.bind=lan",
            )
        return GatewayBindUrlResult(
            error="gateway.bind=lan set, but no private LAN IP was found.",
        )
    return None
