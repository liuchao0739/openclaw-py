"""Token drift resolver for restart checks."""

from __future__ import annotations

from typing import Any

_AUTH_MODES_WITHOUT_TOKEN = frozenset({"password", "none", "trusted-proxy"})


def _auth_mode_disables_token(mode: str | None) -> bool:
    return mode in _AUTH_MODES_WITHOUT_TOKEN


def _is_password_fallback_active(cfg: dict[str, Any], env: dict[str, str]) -> bool:
    """Check if password fallback is active (token auth not winning)."""
    gateway = cfg.get("gateway", {})
    if not isinstance(gateway, dict):
        return False
    auth = gateway.get("auth", {})
    if not isinstance(auth, dict):
        return False
    mode = auth.get("mode")
    if mode:
        return False
    # If no mode is set, check if password can win but token cannot
    has_password = bool(auth.get("password") or env.get("OPENCLAW_GATEWAY_PASSWORD"))
    has_token = bool(auth.get("token") or env.get("OPENCLAW_GATEWAY_TOKEN"))
    return has_password and not has_token


async def resolve_gateway_token_for_drift_check(
    cfg: dict[str, Any] | None = None,
    env: dict[str, str] | None = None,
) -> str | None:
    """Resolve the expected Gateway token for service drift checks.

    Returns None when token auth is inactive.
    """
    import os

    env_map = env or dict(os.environ)
    if not cfg:
        return None

    gateway = cfg.get("gateway", {})
    if not isinstance(gateway, dict):
        return None
    auth = gateway.get("auth", {})
    if not isinstance(auth, dict):
        return None

    mode = auth.get("mode")
    if _auth_mode_disables_token(mode):
        return None

    if _is_password_fallback_active(cfg, env_map):
        return None

    token = auth.get("token")
    if token and isinstance(token, str) and token.strip():
        return token.strip()

    env_token = env_map.get("OPENCLAW_GATEWAY_TOKEN")
    if env_token and env_token.strip():
        return env_token.strip()

    return None
