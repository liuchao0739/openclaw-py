"""Device auth store helpers persist and normalize paired device auth records."""

from __future__ import annotations

import time
from typing import Any, Callable

from .device_auth import (
    DeviceAuthEntry,
    DeviceAuthStore,
    normalize_device_auth_role,
    normalize_device_auth_scopes,
)


def _is_record(value: Any) -> bool:
    return isinstance(value, dict)


def _coerce_device_auth_entry(role: str, value: Any) -> DeviceAuthEntry | None:
    if not _is_record(value) or not isinstance(value.get("token"), str):
        return None
    updated_at_ms = value.get("updatedAtMs", 0)
    if not isinstance(updated_at_ms, (int, float)) or not (updated_at_ms == int(updated_at_ms)) or updated_at_ms < 0:
        updated_at_ms = 0
    if isinstance(updated_at_ms, float):
        updated_at_ms = int(updated_at_ms)
    scopes_raw = value.get("scopes")
    scopes = normalize_device_auth_scopes(scopes_raw if isinstance(scopes_raw, list) else None)
    return DeviceAuthEntry(
        token=value["token"],
        role=role,
        scopes=scopes,
        updated_at_ms=updated_at_ms,
    )


def _copy_canonical_device_auth_tokens(tokens: dict[str, Any]) -> dict[str, DeviceAuthEntry]:
    out: dict[str, DeviceAuthEntry] = {}
    for raw_role, value in tokens.items():
        role = normalize_device_auth_role(raw_role)
        if not role:
            continue
        entry = _coerce_device_auth_entry(role, value)
        if entry:
            out[role] = entry
    return out


def coerce_device_auth_store(value: Any) -> DeviceAuthStore | None:
    if not _is_record(value) or value.get("version") != 1 or not isinstance(value.get("deviceId"), str):
        return None
    if not _is_record(value.get("tokens")):
        return None
    return DeviceAuthStore(
        version=1,
        device_id=value["deviceId"],
        tokens=_copy_canonical_device_auth_tokens(value["tokens"]),
    )


def load_device_auth_token_from_store(
    read_store: Callable[[], DeviceAuthStore | None],
    device_id: str,
    role: str,
) -> DeviceAuthEntry | None:
    store = read_store()
    if not store or store.device_id != device_id:
        return None
    normalized_role = normalize_device_auth_role(role)
    return _coerce_device_auth_entry(normalized_role, store.tokens.get(normalized_role))


def store_device_auth_token_in_store(
    read_store: Callable[[], DeviceAuthStore | None],
    write_store: Callable[[DeviceAuthStore], None],
    device_id: str,
    role: str,
    token: str,
    scopes: list[str] | None = None,
) -> DeviceAuthEntry:
    normalized_role = normalize_device_auth_role(role)
    existing = read_store()
    tokens: dict[str, DeviceAuthEntry] = {}
    if existing and existing.device_id == device_id:
        tokens = _copy_canonical_device_auth_tokens(existing.tokens)
    entry = DeviceAuthEntry(
        token=token,
        role=normalized_role,
        scopes=normalize_device_auth_scopes(scopes),
        updated_at_ms=int(time.time() * 1000),
    )
    tokens[normalized_role] = entry
    next_store = DeviceAuthStore(
        version=1,
        device_id=device_id,
        tokens=tokens,
    )
    write_store(next_store)
    return entry


def clear_device_auth_token_from_store(
    read_store: Callable[[], DeviceAuthStore | None],
    write_store: Callable[[DeviceAuthStore], None],
    device_id: str,
    role: str,
) -> None:
    store = read_store()
    if not store or store.device_id != device_id:
        return
    normalized_role = normalize_device_auth_role(role)
    if normalized_role not in store.tokens:
        return
    next_store = DeviceAuthStore(
        version=1,
        device_id=store.device_id,
        tokens=_copy_canonical_device_auth_tokens(store.tokens),
    )
    next_store.tokens.pop(normalized_role, None)
    write_store(next_store)
