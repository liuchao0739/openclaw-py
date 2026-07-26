"""Elevenlabs API module exposes the plugin public contract."""

from __future__ import annotations

from openclaw_extensions.elevenlabs.config_compat import migrate_eleven_labs_legacy_talk_config
from openclaw_extensions.elevenlabs.doctor_contract import (
    ELEVENLABS_TALK_LEGACY_CONFIG_RULES,
    ELEVENLABS_TALK_PROVIDER_ID,
    has_legacy_talk_fields,
    legacy_config_rules,
    normalize_compatibility_config,
)

__all__ = [
    "ELEVENLABS_TALK_LEGACY_CONFIG_RULES",
    "ELEVENLABS_TALK_PROVIDER_ID",
    "has_legacy_talk_fields",
    "legacy_config_rules",
    "migrate_eleven_labs_legacy_talk_config",
    "normalize_compatibility_config",
]
