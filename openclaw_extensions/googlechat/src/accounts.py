"""Resolves Google Chat account configuration from root channel config.

Mirrors extensions/googlechat/src/accounts.ts.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Literal

from openclaw.channels.plugins.account_helpers import (
    create_account_list_helpers,
    resolve_merged_account_config,
)
from openclaw.config.secrets import coerce_secret_ref
from openclaw.packages.normalization_core import normalize_optional_string
from openclaw.routing.account_id import DEFAULT_ACCOUNT_ID, normalize_account_id
from openclaw.routing.account_lookup import resolve_account_entry

GoogleChatCredentialSource = Literal["file", "inline", "env", "none"]

ENV_SERVICE_ACCOUNT = "GOOGLE_CHAT_SERVICE_ACCOUNT"
ENV_SERVICE_ACCOUNT_FILE = "GOOGLE_CHAT_SERVICE_ACCOUNT_FILE"

_PAIR_LOOP_GUARD_KEYS = (
    "enabled",
    "maxEventsPerWindow",
    "windowSeconds",
    "cooldownSeconds",
)


@dataclass(frozen=True)
class ResolvedGoogleChatAccount:
    account_id: str
    enabled: bool
    config: dict[str, Any]
    credential_source: GoogleChatCredentialSource
    name: str | None = None
    credentials: dict[str, Any] | None = None
    credentials_file: str | None = None


@dataclass(frozen=True)
class GoogleChatConfigAccessorAccount:
    config: dict[str, Any]


_account_helpers = create_account_list_helpers(
    "googlechat",
    implicit_default_account={
        "channelKeys": ["serviceAccount", "serviceAccountRef", "serviceAccountFile"],
        "envVars": [ENV_SERVICE_ACCOUNT, ENV_SERVICE_ACCOUNT_FILE],
    },
)
list_google_chat_account_ids = _account_helpers["list_account_ids"]
resolve_default_google_chat_account_id = _account_helpers["resolve_default_account_id"]


def _merge_pair_loop_guard_config(*configs: dict[str, Any] | None) -> dict[str, Any] | None:
    merged: dict[str, Any] = {}
    has_value = False
    for config in configs:
        if not config:
            continue
        for key in _PAIR_LOOP_GUARD_KEYS:
            if config.get(key) is not None:
                merged[key] = config[key]
                has_value = True
    return merged if has_value else None


def _merge_google_chat_account_config(cfg: dict[str, Any], account_id: str) -> dict[str, Any]:
    raw = (cfg.get("channels") or {}).get("googlechat") or {}
    if not isinstance(raw, dict):
        raw = {}
    accounts = raw.get("accounts") if isinstance(raw.get("accounts"), dict) else None
    base = resolve_merged_account_config(
        channel_config=raw,
        accounts=accounts,
        account_id=account_id,
        omit_keys=["defaultAccount"],
        nested_object_keys=["botLoopProtection"],
    )
    default_account_config = resolve_account_entry(accounts, DEFAULT_ACCOUNT_ID) or {}
    if account_id == DEFAULT_ACCOUNT_ID:
        return base
    ignored_keys = {
        "enabled",
        "dangerouslyAllowNameMatching",
        "serviceAccount",
        "serviceAccountRef",
        "serviceAccountFile",
    }
    default_account_shared = {
        key: value for key, value in default_account_config.items() if key not in ignored_keys
    }
    bot_loop_protection = _merge_pair_loop_guard_config(
        default_account_shared.get("botLoopProtection"),
        base.get("botLoopProtection"),
    )
    merged = {**default_account_shared, **base}
    if bot_loop_protection:
        merged["botLoopProtection"] = bot_loop_protection
    return merged


def resolve_google_chat_config_accessor_account(
    *,
    cfg: dict[str, Any],
    account_id: str | None = None,
) -> GoogleChatConfigAccessorAccount:
    channel = (cfg.get("channels") or {}).get("googlechat")
    default_account = channel.get("defaultAccount") if isinstance(channel, dict) else None
    resolved_account_id = normalize_account_id(account_id or default_account)
    return GoogleChatConfigAccessorAccount(
        config=_merge_google_chat_account_config(cfg, resolved_account_id)
    )


def _parse_service_account(value: object) -> dict[str, Any] | None:
    if coerce_secret_ref(value):
        return None
    if isinstance(value, str):
        trimmed = value.strip()
        if not trimmed:
            return None
        try:
            parsed = json.loads(trimmed)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None
    return value if isinstance(value, dict) else None


def _resolve_credentials_from_config(
    *,
    account_id: str,
    account: dict[str, Any],
) -> dict[str, Any]:
    inline = _parse_service_account(account.get("serviceAccount"))
    if inline:
        return {"credentials": inline, "source": "inline"}

    service_account = account.get("serviceAccount")
    if coerce_secret_ref(service_account):
        ref = coerce_secret_ref(service_account)
        assert ref is not None
        raise ValueError(
            f"channels.googlechat.accounts.{account_id}.serviceAccount: unresolved SecretRef "
            f'"{ref.source}:{ref.provider}:{ref.id}". Resolve this command against an active '
            "gateway runtime snapshot before reading it."
        )

    service_account_ref = account.get("serviceAccountRef")
    if coerce_secret_ref(service_account_ref):
        ref = coerce_secret_ref(service_account_ref)
        assert ref is not None
        raise ValueError(
            f"channels.googlechat.accounts.{account_id}.serviceAccount: unresolved SecretRef "
            f'"{ref.source}:{ref.provider}:{ref.id}". Resolve this command against an active '
            "gateway runtime snapshot before reading it."
        )

    file_path = normalize_optional_string(account.get("serviceAccountFile"))
    if file_path:
        return {"credentials_file": file_path, "source": "file"}

    if account_id == DEFAULT_ACCOUNT_ID:
        env_inline = _parse_service_account(os.environ.get(ENV_SERVICE_ACCOUNT))
        if env_inline:
            return {"credentials": env_inline, "source": "env"}
        env_file = normalize_optional_string(os.environ.get(ENV_SERVICE_ACCOUNT_FILE))
        if env_file:
            return {"credentials_file": env_file, "source": "env"}

    return {"source": "none"}


def resolve_google_chat_account(
    *,
    cfg: dict[str, Any],
    account_id: str | None = None,
) -> ResolvedGoogleChatAccount:
    channel = (cfg.get("channels") or {}).get("googlechat")
    default_account = channel.get("defaultAccount") if isinstance(channel, dict) else None
    resolved_account_id = normalize_account_id(account_id or default_account)
    base_enabled = True
    if isinstance(channel, dict) and channel.get("enabled") is False:
        base_enabled = False
    merged = _merge_google_chat_account_config(cfg, resolved_account_id)
    account_enabled = merged.get("enabled") is not False
    enabled = base_enabled and account_enabled
    credentials = _resolve_credentials_from_config(account_id=resolved_account_id, account=merged)
    return ResolvedGoogleChatAccount(
        account_id=resolved_account_id,
        name=normalize_optional_string(merged.get("name")),
        enabled=enabled,
        config=merged,
        credential_source=credentials["source"],
        credentials=credentials.get("credentials"),
        credentials_file=credentials.get("credentials_file"),
    )
