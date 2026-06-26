"""WebSocket auth messages format client-specific handshake failures without
exposing secret material.

Mirrors src/gateway/server/ws-connection/auth-messages.ts.
"""

from __future__ import annotations

from typing import Any, Literal, Mapping

AuthProvidedKind = Literal["token", "bootstrap-token", "device-token", "password", "none"]


def _is_gateway_cli_client(client: Mapping[str, Any] | None) -> bool:
    if not client:
        return False
    mode = client.get("mode") or ""
    cid = client.get("id") or ""
    return mode == "cli" or cid.startswith("cli:")


def _is_operator_ui_client(client: Mapping[str, Any] | None) -> bool:
    if not client:
        return False
    mode = client.get("mode") or ""
    cid = client.get("id") or ""
    return mode == "operator-ui" or cid.startswith("operator-ui:")


def _is_webchat_client(client: Mapping[str, Any] | None) -> bool:
    if not client:
        return False
    mode = client.get("mode") or ""
    cid = client.get("id") or ""
    return mode == "webchat" or cid.startswith("webchat:")


def format_gateway_auth_failure_message(
    params: Mapping[str, Any],
) -> str:
    """Format a client-specific auth failure message without exposing secret values."""
    auth_mode = params.get("authMode", "")
    auth_provided = params.get("authProvided", "none")
    reason = params.get("reason")
    client = params.get("client")

    is_cli = _is_gateway_cli_client(client)
    is_control_ui = _is_operator_ui_client(client)
    is_webchat = _is_webchat_client(client)

    ui_hint = "open the dashboard URL and paste the token in Control UI settings"
    if is_cli:
        token_hint = "set gateway.remote.token to match gateway.auth.token"
    elif is_control_ui or is_webchat:
        token_hint = ui_hint
    else:
        token_hint = "provide gateway auth token"

    if is_cli:
        password_hint = "set gateway.remote.password to match gateway.auth.password"
    elif is_control_ui or is_webchat:
        password_hint = "enter the password in Control UI settings"
    else:
        password_hint = "provide gateway auth password"

    reason_messages: dict[str, str] = {
        "token_missing": f"unauthorized: gateway token missing ({token_hint})",
        "token_mismatch": f"unauthorized: gateway token mismatch ({token_hint})",
        "token_missing_config": "unauthorized: gateway token not configured on gateway (set gateway.auth.token)",
        "password_missing": f"unauthorized: gateway password missing ({password_hint})",
        "password_mismatch": f"unauthorized: gateway password mismatch ({password_hint})",
        "password_missing_config": "unauthorized: gateway password not configured on gateway (set gateway.auth.password)",
        "bootstrap_token_invalid": "unauthorized: bootstrap token invalid or expired (scan a fresh setup code)",
        "tailscale_user_missing": "unauthorized: tailscale identity missing (use Tailscale Serve auth or gateway token/password)",
        "tailscale_proxy_missing": "unauthorized: tailscale proxy headers missing (use Tailscale Serve or gateway token/password)",
        "tailscale_whois_failed": "unauthorized: tailscale identity check failed (use Tailscale Serve auth or gateway token/password)",
        "tailscale_user_mismatch": "unauthorized: tailscale identity mismatch (use Tailscale Serve auth or gateway token/password)",
        "rate_limited": "unauthorized: too many failed authentication attempts (retry later)",
        "device_token_mismatch": "unauthorized: device token mismatch (rotate/reissue device token)",
        "scope_mismatch": "unauthorized: device token scope mismatch (re-pair or approve scope upgrade)",
    }

    if reason and reason in reason_messages:
        return reason_messages[reason]

    if auth_mode == "token" and auth_provided == "none":
        return f"unauthorized: gateway token missing ({token_hint})"
    if auth_mode == "token" and auth_provided == "device-token":
        return "unauthorized: device token rejected (pair/repair this device, or provide gateway token)"
    if auth_provided == "bootstrap-token":
        return "unauthorized: bootstrap token invalid or expired (scan a fresh setup code)"
    if auth_mode == "password" and auth_provided == "none":
        return f"unauthorized: gateway password missing ({password_hint})"
    return "unauthorized"
