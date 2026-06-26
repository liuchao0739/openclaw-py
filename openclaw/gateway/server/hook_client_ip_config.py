"""Hook client-IP config adapts gateway trusted-proxy settings for hook request handling.

Mirrors src/gateway/server/hook-client-ip-config.ts.
"""

from __future__ import annotations

from typing import Any, Mapping


def resolve_hook_client_ip_config(cfg: Mapping[str, Any] | None) -> dict[str, Any]:
    """Adapt gateway network trust config to the hooks HTTP request handler."""
    cfg = cfg or {}
    gateway = cfg.get("gateway") or {}
    return {
        "trusted_proxies": gateway.get("trustedProxies"),
        "allow_real_ip_fallback": gateway.get("allowRealIpFallback") is True,
    }
