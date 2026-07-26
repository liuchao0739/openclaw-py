"""Elevenlabs plugin module implements doctor contract behavior."""

from __future__ import annotations

from typing import Any

from openclaw.packages.normalization_core import is_record
from openclaw_extensions.elevenlabs.config_compat import (
    ELEVENLABS_TALK_PROVIDER_ID,
    migrate_eleven_labs_legacy_talk_config,
)

_LEGACY_TALK_FIELD_KEYS = ("voiceId", "voiceAliases", "modelId", "outputFormat", "apiKey")


def has_legacy_talk_fields(value: Any) -> bool:
    talk = value if is_record(value) else None
    if talk is None:
        return False
    return any(key in talk for key in _LEGACY_TALK_FIELD_KEYS)


legacy_config_rules: list[dict[str, Any]] = [
    {
        "path": ["talk"],
        "message": (
            "talk.voiceId/talk.voiceAliases/talk.modelId/talk.outputFormat/talk.apiKey are legacy; "
            "use talk.providers.<provider> and run openclaw doctor --fix."
        ),
        "match": has_legacy_talk_fields,
    },
]

ELEVENLABS_TALK_LEGACY_CONFIG_RULES = legacy_config_rules


def normalize_compatibility_config(params: dict[str, Any]) -> dict[str, Any]:
    cfg = params.get("cfg")
    return migrate_eleven_labs_legacy_talk_config(cfg)
