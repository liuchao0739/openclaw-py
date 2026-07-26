"""Tests for speech-core speaker selection compatibility helpers."""

from __future__ import annotations

from openclaw_packages.speech_core import (
    with_speaker_selection_compat,
    with_speaker_selection_fallback_compat,
)


def test_with_speaker_selection_compat_populates_canonical_and_legacy_fields() -> None:
    assert with_speaker_selection_compat(
        {
            "speakerVoice": "cedar",
            "speakerVoiceId": "voice-123",
        },
    ) == {
        "speakerVoice": "cedar",
        "speakerVoiceId": "voice-123",
        "voice": "cedar",
        "voiceName": "cedar",
        "voiceId": "voice-123",
    }
    assert with_speaker_selection_compat(
        {
            "voiceName": "marin",
            "voiceId": "voice-456",
        },
    ) == {
        "voiceName": "marin",
        "voiceId": "voice-456",
        "speakerVoice": "marin",
        "voice": "marin",
        "speakerVoiceId": "voice-456",
    }
    assert with_speaker_selection_compat(None) == {}


def test_with_speaker_selection_fallback_compat_only_fills_missing_legacy_fields() -> None:
    assert with_speaker_selection_fallback_compat(
        {
            "speakerVoice": "cedar",
            "speakerVoiceId": "voice-123",
            "voice": "existing-voice",
        },
    ) == {
        "speakerVoice": "cedar",
        "speakerVoiceId": "voice-123",
        "voice": "existing-voice",
        "voiceName": "cedar",
        "voiceId": "voice-123",
    }
    assert with_speaker_selection_fallback_compat(
        {
            "speakerVoice": "cedar",
            "voice": "",
        },
    ) == {
        "speakerVoice": "cedar",
        "voice": "",
        "voiceName": "cedar",
    }
