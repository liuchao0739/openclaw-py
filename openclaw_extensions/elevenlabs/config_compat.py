"""Elevenlabs helper module supports config compat behavior."""

from __future__ import annotations

import copy
import os
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Protocol

from openclaw.packages.normalization_core import is_record

ELEVENLABS_API_KEY_ENV = "ELEVENLABS_API_KEY"
PROFILE_CANDIDATES = (".profile", ".zprofile", ".zshrc", ".bashrc")
LEGACY_TALK_FIELD_KEYS = ("voiceId", "voiceAliases", "modelId", "outputFormat", "apiKey")

ELEVENLABS_TALK_PROVIDER_ID = "elevenlabs"

_BLOCKED_OBJECT_KEYS = frozenset({"__proto__", "prototype", "constructor"})
_PROFILE_API_KEY_PATTERN = re.compile(
    r'(?:^|\n)\s*(?:export\s+)?ELEVENLABS_API_KEY\s*=\s*["\']?([^\n"\']+)["\']?',
)


class _FsLike(Protocol):
    def exists(self, path: str | os.PathLike[str]) -> bool: ...

    def read_text(self, path: str | os.PathLike[str], encoding: str = "utf-8") -> str: ...


def _get_record(value: Any) -> dict[str, Any] | None:
    return value if is_record(value) else None


def _ensure_record(root: dict[str, Any], key: str) -> dict[str, Any]:
    existing = _get_record(root.get(key))
    if existing is not None:
        return existing
    next_record: dict[str, Any] = {}
    root[key] = next_record
    return next_record


def _is_blocked_object_key(key: str) -> bool:
    return key in _BLOCKED_OBJECT_KEYS


def _merge_missing(target: dict[str, Any], source: Mapping[str, Any]) -> None:
    for key, value in source.items():
        if value is None or _is_blocked_object_key(key):
            continue
        existing = target.get(key)
        if existing is None:
            target[key] = value
            continue
        if is_record(existing) and is_record(value):
            _merge_missing(existing, value)


def _has_legacy_talk_fields(value: Any) -> bool:
    talk = _get_record(value)
    if talk is None:
        return False
    return any(key in talk for key in LEGACY_TALK_FIELD_KEYS)


def _resolve_talk_migration_target_provider_id(talk: dict[str, Any]) -> str | None:
    explicit_provider_raw = talk.get("provider")
    explicit_provider = (
        explicit_provider_raw.strip()
        if isinstance(explicit_provider_raw, str) and explicit_provider_raw.strip()
        else None
    )
    providers = _get_record(talk.get("providers"))
    if explicit_provider:
        if _is_blocked_object_key(explicit_provider):
            return None
        return explicit_provider
    if providers is None:
        return ELEVENLABS_TALK_PROVIDER_ID
    provider_ids = [key for key in providers if not _is_blocked_object_key(key)]
    if not provider_ids:
        return ELEVENLABS_TALK_PROVIDER_ID
    if len(provider_ids) == 1:
        return provider_ids[0]
    return None


def migrate_eleven_labs_legacy_talk_config(raw: Any) -> dict[str, Any]:
    if not is_record(raw):
        return {"config": raw, "changes": []}

    talk = _get_record(raw.get("talk"))
    if talk is None or not _has_legacy_talk_fields(talk):
        return {"config": raw, "changes": []}

    provider_id = _resolve_talk_migration_target_provider_id(talk)
    if provider_id is None:
        return {
            "config": raw,
            "changes": [
                "Skipped talk legacy field migration because talk.providers defines multiple providers and talk.provider is unset; move talk.voiceId/talk.voiceAliases/talk.modelId/talk.outputFormat/talk.apiKey under the intended provider manually.",
            ],
        }

    next_root = copy.deepcopy(raw)
    next_talk = _ensure_record(next_root, "talk")
    providers = _ensure_record(next_talk, "providers")
    existing_provider = _get_record(providers.get(provider_id)) or {}
    migrated_provider = copy.deepcopy(existing_provider)
    legacy_fields: dict[str, Any] = {}
    moved_keys: list[str] = []

    for key in LEGACY_TALK_FIELD_KEYS:
        if key not in next_talk:
            continue
        legacy_fields[key] = next_talk[key]
        del next_talk[key]
        moved_keys.append(key)

    if not moved_keys:
        return {"config": raw, "changes": []}

    _merge_missing(migrated_provider, legacy_fields)
    providers[provider_id] = migrated_provider
    next_talk["providers"] = providers
    next_root["talk"] = next_talk

    return {
        "config": next_root,
        "changes": [
            f"Moved talk legacy fields ({', '.join(moved_keys)}) → talk.providers.{provider_id} (filled missing provider fields only).",
        ],
    }


def _read_api_key_from_profile(
    *,
    fs: _FsLike | None = None,
    home: str | Path | None = None,
) -> str | None:
    home_path = Path(home or Path.home())
    path_impl = Path if fs is None else None

    for candidate in PROFILE_CANDIDATES:
        full_path = home_path / candidate
        try:
            if fs is not None:
                if not fs.exists(full_path):
                    continue
                text = fs.read_text(full_path, encoding="utf-8")
            else:
                if not full_path.exists():
                    continue
                text = full_path.read_text(encoding="utf-8")
        except OSError:
            continue
        match = _PROFILE_API_KEY_PATTERN.search(text)
        value = match.group(1).strip() if match else ""
        if value:
            return value
    return None


def resolve_eleven_labs_api_key_with_profile_fallback(
    env: Mapping[str, str] | None = None,
    *,
    fs: _FsLike | None = None,
    home: str | Path | None = None,
) -> str | None:
    resolved_env = env if env is not None else os.environ
    env_value = (resolved_env.get(ELEVENLABS_API_KEY_ENV) or "").strip()
    if env_value:
        return env_value
    return _read_api_key_from_profile(fs=fs, home=home)
