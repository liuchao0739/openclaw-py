"""Speaker-selection compatibility helpers for plugins that renamed voice fields.

Mirrors packages/speech-core/speaker.ts.
"""

from __future__ import annotations

from typing import Any

from openclaw.packages.normalization_core import normalize_optional_string

__all__ = [
    "SpeakerSelectionConfig",
    "with_speaker_selection_compat",
    "with_speaker_selection_fallback_compat",
]

SpeakerSelectionConfig = dict[str, Any]


def with_speaker_selection_compat(
    config: SpeakerSelectionConfig | None,
) -> SpeakerSelectionConfig:
    """Populate canonical and legacy speaker voice fields together."""
    next_config: SpeakerSelectionConfig = dict(config) if config else {}
    speaker_voice = normalize_optional_string(next_config.get("speakerVoice"))
    speaker_voice_id = normalize_optional_string(next_config.get("speakerVoiceId"))
    voice = normalize_optional_string(next_config.get("voice"))
    voice_name = normalize_optional_string(next_config.get("voiceName"))
    voice_id = normalize_optional_string(next_config.get("voiceId"))
    canonical_voice = speaker_voice or voice or voice_name
    canonical_voice_id = speaker_voice_id or voice_id
    if canonical_voice:
        next_config["speakerVoice"] = canonical_voice
        next_config["voice"] = canonical_voice
        next_config["voiceName"] = canonical_voice
    if canonical_voice_id:
        next_config["speakerVoiceId"] = canonical_voice_id
        next_config["voiceId"] = canonical_voice_id
    return next_config


def with_speaker_selection_fallback_compat(
    config: SpeakerSelectionConfig | None,
) -> SpeakerSelectionConfig:
    """Fill legacy speaker fields only when callers have not set them explicitly."""
    next_config: SpeakerSelectionConfig = dict(config) if config else {}
    speaker_voice = normalize_optional_string(next_config.get("speakerVoice"))
    speaker_voice_id = normalize_optional_string(next_config.get("speakerVoiceId"))
    if speaker_voice:
        if next_config.get("voice") is None:
            next_config["voice"] = speaker_voice
        if next_config.get("voiceName") is None:
            next_config["voiceName"] = speaker_voice
    if speaker_voice_id and next_config.get("voiceId") is None:
        next_config["voiceId"] = speaker_voice_id
    return next_config
