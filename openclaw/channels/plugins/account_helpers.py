"""Channel plugin account helper factory.

Mirrors src/channels/plugins/account-helpers.ts.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any, TypeVar

from openclaw.plugins.contracts.shared import unique_strings
from openclaw.routing.account_id import (
    DEFAULT_ACCOUNT_ID,
    normalize_account_id,
    normalize_optional_account_id,
)
from openclaw.routing.account_lookup import resolve_account_entry, resolve_normalized_account_entry

TConfig = TypeVar("TConfig", bound=dict[str, Any])


def has_configured_account_value(value: object) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    return value is not None


def list_combined_account_ids(
    *,
    configured_account_ids: Iterable[str],
    additional_account_ids: Iterable[str] | None = None,
    implicit_account_id: str | None = None,
    fallback_account_id_when_empty: str | None = None,
) -> list[str]:
    ids: set[str] = set()
    for account_id in configured_account_ids:
        if account_id:
            ids.add(account_id)
    for account_id in additional_account_ids or []:
        if account_id:
            ids.add(account_id)
    if implicit_account_id:
        ids.add(implicit_account_id)
    if not ids and fallback_account_id_when_empty:
        return [fallback_account_id_when_empty]
    return sorted(ids)


def resolve_listed_default_account_id(
    *,
    account_ids: list[str],
    configured_default_account_id: str | None = None,
    allow_unlisted_default_account: bool = False,
    ambiguous_fallback_account_id: str | None = None,
    normalize_listed_account_id: Callable[[str], str] | None = None,
) -> str:
    normalize_fn = normalize_listed_account_id or normalize_account_id
    preferred = configured_default_account_id
    if preferred and (
        allow_unlisted_default_account
        or any(normalize_fn(account_id) == preferred for account_id in account_ids)
    ):
        return preferred
    if DEFAULT_ACCOUNT_ID in account_ids:
        return DEFAULT_ACCOUNT_ID
    if ambiguous_fallback_account_id and len(account_ids) > 1:
        return ambiguous_fallback_account_id
    return account_ids[0] if account_ids else DEFAULT_ACCOUNT_ID


def merge_account_config(
    *,
    channel_config: TConfig | None,
    account_config: dict[str, Any] | None,
    omit_keys: list[str] | None = None,
    nested_object_keys: list[str] | None = None,
) -> TConfig:
    omit = {"accounts", *(omit_keys or [])}
    base = {key: value for key, value in (channel_config or {}).items() if key not in omit}
    merged: dict[str, Any] = {**base, **(account_config or {})}
    for key in nested_object_keys or []:
        base_value = base.get(key)
        account_value = (account_config or {}).get(key)
        if (
            isinstance(base_value, dict)
            and base_value is not None
            and isinstance(account_value, dict)
            and account_value is not None
        ):
            merged[key] = {**base_value, **account_value}
    return merged  # type: ignore[return-value]


def resolve_merged_account_config(
    *,
    channel_config: TConfig | None,
    accounts: dict[str, dict[str, Any]] | None,
    account_id: str,
    omit_keys: list[str] | None = None,
    normalize_account_id_fn: Callable[[str], str] | None = None,
    nested_object_keys: list[str] | None = None,
) -> TConfig:
    if normalize_account_id_fn is not None:
        account_config = resolve_normalized_account_entry(
            accounts,
            account_id,
            normalize_account_id_fn,
        )
    else:
        account_config = resolve_account_entry(accounts, account_id)
    return merge_account_config(
        channel_config=channel_config,
        account_config=account_config,
        omit_keys=omit_keys,
        nested_object_keys=nested_object_keys,
    )


def create_account_list_helpers(
    channel_key: str,
    *,
    normalize_account_id_fn: Callable[[str], str] | None = None,
    allow_unlisted_default_account: bool = False,
    implicit_default_account: dict[str, list[str]] | None = None,
    has_implicit_default_account: Callable[[dict[str, Any]], bool] | None = None,
) -> dict[str, Callable[..., Any]]:
    channel_keys = (implicit_default_account or {}).get("channelKeys", [])
    env_vars = (implicit_default_account or {}).get("envVars", [])

    def _has_implicit_default_account(cfg: dict[str, Any]) -> bool:
        if has_implicit_default_account is not None and has_implicit_default_account(cfg):
            return True
        channel = (cfg.get("channels") or {}).get(channel_key)
        if isinstance(channel, dict):
            for key in channel_keys:
                if has_configured_account_value(channel.get(key)):
                    return True
        import os

        for key in env_vars:
            if has_configured_account_value(os.environ.get(key)):
                return True
        return False

    def _resolve_configured_default_account_id(cfg: dict[str, Any]) -> str | None:
        channel = (cfg.get("channels") or {}).get(channel_key)
        if not isinstance(channel, dict):
            return None
        preferred = normalize_optional_account_id(
            channel.get("defaultAccount")
            if isinstance(channel.get("defaultAccount"), str)
            else None
        )
        if not preferred:
            return None
        ids = list_account_ids(cfg)
        if allow_unlisted_default_account:
            return preferred
        if any(normalize_account_id(account_id) == preferred for account_id in ids):
            return preferred
        return None

    def list_configured_account_ids(cfg: dict[str, Any]) -> list[str]:
        channel = (cfg.get("channels") or {}).get(channel_key)
        if not isinstance(channel, dict):
            return []
        accounts = channel.get("accounts")
        if not isinstance(accounts, dict):
            return []
        ids = [account_id for account_id in accounts if account_id]
        if normalize_account_id_fn is None:
            return ids
        return unique_strings(ids, normalize=normalize_account_id_fn)

    def list_account_ids(cfg: dict[str, Any]) -> list[str]:
        return list_combined_account_ids(
            configured_account_ids=list_configured_account_ids(cfg),
            implicit_account_id=DEFAULT_ACCOUNT_ID if _has_implicit_default_account(cfg) else None,
            fallback_account_id_when_empty=DEFAULT_ACCOUNT_ID,
        )

    def resolve_default_account_id(cfg: dict[str, Any]) -> str:
        return resolve_listed_default_account_id(
            account_ids=list_account_ids(cfg),
            configured_default_account_id=_resolve_configured_default_account_id(cfg),
            allow_unlisted_default_account=allow_unlisted_default_account,
        )

    return {
        "list_configured_account_ids": list_configured_account_ids,
        "list_account_ids": list_account_ids,
        "resolve_default_account_id": resolve_default_account_id,
    }
