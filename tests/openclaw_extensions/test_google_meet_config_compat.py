"""Tests for Google Meet config compatibility migration."""

from __future__ import annotations

from openclaw_extensions.google_meet.src.config_compat import (
    legacy_config_rules,
    migrate_google_meet_legacy_realtime_provider,
    normalize_compatibility_config,
)


def test_detects_legacy_google_realtime_provider_config() -> None:
    assert legacy_config_rules[0]["match"](
        {
            "provider": "google",
            "model": "gemini-2.5-flash-native-audio-preview-12-2025",
        }
    ) is True


def test_migrates_legacy_google_bidi_provider_intent_to_scoped_realtime_providers() -> None:
    config = {
        "plugins": {
            "entries": {
                "google-meet": {
                    "enabled": True,
                    "config": {
                        "defaultMode": "agent",
                        "realtime": {
                            "provider": "google",
                            "model": "gemini-2.5-flash-native-audio-preview-12-2025",
                            "providers": {
                                "google": {
                                    "voice": "Kore",
                                },
                            },
                        },
                    },
                },
            },
        },
    }

    migration = migrate_google_meet_legacy_realtime_provider(config)

    assert migration is not None
    assert migration["changes"] == [
        'Moved Google Meet legacy realtime.provider="google" intent to '
        'realtime.voiceProvider="google" and realtime.transcriptionProvider="openai".',
    ]
    realtime = (
        migration["config"]["plugins"]["entries"]["google-meet"]["config"]["realtime"]
    )
    assert realtime == {
        "provider": "openai",
        "transcriptionProvider": "openai",
        "voiceProvider": "google",
        "model": "gemini-2.5-flash-native-audio-preview-12-2025",
        "providers": {
            "google": {
                "voice": "Kore",
            },
        },
    }


def test_leaves_fully_scoped_provider_configs_alone() -> None:
    config = {
        "plugins": {
            "entries": {
                "google-meet": {
                    "config": {
                        "realtime": {
                            "provider": "google",
                            "transcriptionProvider": "custom-stt",
                            "voiceProvider": "custom-voice",
                        },
                    },
                },
            },
        },
    }

    migration = normalize_compatibility_config(config)

    assert migration["changes"] == []
    realtime = migration["config"]["plugins"]["entries"]["google-meet"]["config"]["realtime"]
    assert realtime == {
        "provider": "google",
        "transcriptionProvider": "custom-stt",
        "voiceProvider": "custom-voice",
    }
