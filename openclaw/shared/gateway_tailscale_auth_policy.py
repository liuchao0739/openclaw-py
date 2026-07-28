"""Gateway Tailscale auth policy helpers describe auth requirements for Tailscale modes."""

from __future__ import annotations


def is_unsafe_gateway_tailscale_no_auth(
    auth_mode: str | None = None,
    tailscale_mode: str | None = None,
) -> bool:
    return (
        auth_mode == "none"
        and tailscale_mode in ("serve", "funnel")
    )


def format_unsafe_gateway_tailscale_no_auth_message(tailscale_mode: str) -> str:
    if tailscale_mode == "funnel":
        return "gateway.tailscale.mode=funnel requires gateway.auth.mode=password; auth.mode=none cannot be used when exposing the gateway through Tailscale Funnel"
    return f"gateway.auth.mode=none cannot be used with gateway.tailscale.mode={tailscale_mode}; configure token, password, or trusted-proxy auth before exposing the gateway through Tailscale"
