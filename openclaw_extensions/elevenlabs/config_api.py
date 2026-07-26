"""Narrow barrel for ElevenLabs config compatibility helpers consumed outside the plugin."""

from __future__ import annotations

from openclaw_extensions.elevenlabs.config_compat import (
    ELEVENLABS_TALK_PROVIDER_ID,
    migrate_eleven_labs_legacy_talk_config,
    resolve_eleven_labs_api_key_with_profile_fallback,
)

__all__ = [
    "ELEVENLABS_TALK_PROVIDER_ID",
    "migrate_eleven_labs_legacy_talk_config",
    "resolve_eleven_labs_api_key_with_profile_fallback",
]
