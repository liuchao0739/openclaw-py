"""Google Meet config compatibility migration helpers."""

from __future__ import annotations

import copy
from collections.abc import Callable
from typing import Any, TypedDict

from openclaw.packages.normalization_core import as_record, normalize_optional_lowercase_string


class LegacyConfigRule(TypedDict):
    path: list[str | int]
    message: str
    match: Callable[[Any], bool]


def _has_own(record: dict[str, Any], key: str) -> bool:
    return key in record


def _has_legacy_google_realtime_provider(value: Any) -> bool:
    realtime = as_record(value)
    if not realtime or normalize_optional_lowercase_string(realtime.get("provider")) != "google":
        return False
    return not _has_own(realtime, "voiceProvider") or not _has_own(realtime, "transcriptionProvider")


legacy_config_rules: list[LegacyConfigRule] = [
    {
        "path": ["plugins", "entries", "google-meet", "config", "realtime"],
        "message": (
            'plugins.entries.google-meet.config.realtime.provider="google" is legacy for Gemini Live '
            "bidi mode; use realtime.voiceProvider=\"google\" and realtime.transcriptionProvider=\"openai\". "
            'Run "openclaw doctor --fix".'
        ),
        "match": _has_legacy_google_realtime_provider,
    },
]


def migrate_google_meet_legacy_realtime_provider(config: dict[str, Any]) -> dict[str, Any] | None:
    plugins = as_record(config.get("plugins"))
    entries = as_record(plugins.get("entries")) if plugins else None
    raw_entry = as_record(entries.get("google-meet")) if entries else None
    raw_plugin_config = as_record(raw_entry.get("config")) if raw_entry else None
    raw_realtime = as_record(raw_plugin_config.get("realtime")) if raw_plugin_config else None
    if not raw_realtime or not _has_legacy_google_realtime_provider(raw_realtime):
        return None

    next_config = copy.deepcopy(config)
    next_plugins = as_record(next_config.setdefault("plugins", {}))
    next_entries = as_record(next_plugins.setdefault("entries", {}))
    next_entry = as_record(next_entries.setdefault("google-meet", {}))
    next_plugin_config = as_record(next_entry.setdefault("config", {}))
    next_realtime = as_record(next_plugin_config.setdefault("realtime", {}))

    next_realtime["provider"] = "openai"
    if not _has_own(next_realtime, "transcriptionProvider"):
        next_realtime["transcriptionProvider"] = "openai"
    if not _has_own(next_realtime, "voiceProvider"):
        next_realtime["voiceProvider"] = "google"

    return {
        "config": next_config,
        "changes": [
            'Moved Google Meet legacy realtime.provider="google" intent to '
            'realtime.voiceProvider="google" and realtime.transcriptionProvider="openai".',
        ],
    }


def normalize_compatibility_config(cfg: dict[str, Any]) -> dict[str, Any]:
    migrated = migrate_google_meet_legacy_realtime_provider(cfg)
    if migrated is not None:
        return migrated
    return {"config": cfg, "changes": []}
