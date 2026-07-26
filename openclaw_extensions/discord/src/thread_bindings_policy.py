"""Thread-binding policy resolution for channel/account session spawning."""

from __future__ import annotations

from typing import Any, Literal

from openclaw.packages.normalization_core import normalize_lowercase_string_or_empty
from openclaw.routing.account_id import normalize_account_id

ThreadBindingSpawnKind = Literal["subagent", "acp"]


def _normalize_boolean(value: object) -> bool | None:
    return value if isinstance(value, bool) else None


def _resolve_channel_thread_bindings(
    *,
    cfg: dict[str, Any],
    channel: str,
    account_id: str,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    channels = cfg.get("channels") or {}
    channel_config = channels.get(channel) if isinstance(channels, dict) else None
    if not isinstance(channel_config, dict):
        return None, None
    accounts = channel_config.get("accounts")
    account_config = accounts.get(account_id) if isinstance(accounts, dict) else None
    return channel_config.get("threadBindings"), (
        account_config.get("threadBindings") if isinstance(account_config, dict) else None
    )


def _resolve_spawn_flag_key(kind: ThreadBindingSpawnKind) -> str:
    return "spawnSubagentSessions" if kind == "subagent" else "spawnAcpSessions"


def resolve_thread_binding_spawn_policy(
    *,
    cfg: dict[str, Any],
    channel: str,
    account_id: str | None = None,
    kind: ThreadBindingSpawnKind,
) -> dict[str, Any]:
    normalized_channel = normalize_lowercase_string_or_empty(channel)
    resolved_account_id = normalize_account_id(account_id)
    root, account = _resolve_channel_thread_bindings(
        cfg=cfg,
        channel=normalized_channel,
        account_id=resolved_account_id,
    )
    session_bindings = ((cfg.get("session") or {}).get("threadBindings") or {})

    def _coalesce_bool(*values: object) -> bool:
        for value in values:
            normalized = _normalize_boolean(value)
            if normalized is not None:
                return normalized
        return True

    enabled = _coalesce_bool(
        (account or {}).get("enabled"),
        (root or {}).get("enabled"),
        session_bindings.get("enabled"),
        True,
    )
    spawn_flag_key = _resolve_spawn_flag_key(kind)
    spawn_enabled = _coalesce_bool(
        (account or {}).get(spawn_flag_key),
        (account or {}).get("spawnSessions"),
        (root or {}).get(spawn_flag_key),
        (root or {}).get("spawnSessions"),
        session_bindings.get("spawnSessions"),
        True,
    )
    default_spawn_context = (
        (account or {}).get("defaultSpawnContext")
        or (root or {}).get("defaultSpawnContext")
        or session_bindings.get("defaultSpawnContext")
        or "fork"
    )
    return {
        "channel": normalized_channel,
        "accountId": resolved_account_id,
        "enabled": enabled,
        "spawnEnabled": spawn_enabled,
        "defaultSpawnContext": default_spawn_context,
    }


def format_thread_binding_disabled_error(
    *,
    channel: str,
    account_id: str,
    kind: ThreadBindingSpawnKind,
) -> str:
    return (
        f"Thread bindings are disabled for {channel} "
        f"(set channels.{channel}.threadBindings.enabled=true to override for this account, "
        "or session.threadBindings.enabled=true globally)."
    )


def format_thread_binding_spawn_disabled_error(
    *,
    channel: str,
    account_id: str,
    kind: ThreadBindingSpawnKind,
) -> str:
    return (
        f"Thread-bound session spawns are disabled for {channel} "
        f"(set channels.{channel}.threadBindings.spawnSessions=true to enable)."
    )


__all__ = [
    "format_thread_binding_disabled_error",
    "format_thread_binding_spawn_disabled_error",
    "resolve_thread_binding_spawn_policy",
]
