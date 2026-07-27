"""Tests for Google Meet gateway operation timeout resolution."""

from __future__ import annotations

from openclaw_packages.normalization_core.number_coercion import MAX_TIMER_TIMEOUT_MS
from openclaw_extensions.google_meet.src.config import (
    resolve_google_meet_config,
    resolve_google_meet_gateway_operation_timeout_ms,
)


def test_caps_timer_config_fields_before_runtime_polling_uses_them() -> None:
    config = resolve_google_meet_config(
        {
            "chrome": {
                "joinTimeoutMs": float("inf"),
                "waitForInCallMs": float("inf"),
                "bargeInCooldownMs": float("inf"),
            },
            "voiceCall": {
                "requestTimeoutMs": float("inf"),
                "dtmfDelayMs": float("inf"),
                "postDtmfSpeechDelayMs": float("inf"),
            },
        }
    )

    assert config.chrome.join_timeout_ms == MAX_TIMER_TIMEOUT_MS
    assert config.chrome.wait_for_in_call_ms == MAX_TIMER_TIMEOUT_MS
    assert config.chrome.barge_in_cooldown_ms == MAX_TIMER_TIMEOUT_MS
    assert config.voice_call.request_timeout_ms == MAX_TIMER_TIMEOUT_MS
    assert config.voice_call.dtmf_delay_ms == MAX_TIMER_TIMEOUT_MS
    assert config.voice_call.post_dtmf_speech_delay_ms == MAX_TIMER_TIMEOUT_MS


def test_adds_operation_grace_to_normal_transport_timeouts() -> None:
    assert resolve_google_meet_gateway_operation_timeout_ms(resolve_google_meet_config({})) == 60_000
    assert (
        resolve_google_meet_gateway_operation_timeout_ms(
            resolve_google_meet_config(
                {
                    "chrome": {"joinTimeoutMs": 120_000},
                    "voiceCall": {"requestTimeoutMs": 30_000},
                }
            )
        )
        == 150_000
    )


def test_caps_overflowed_transport_timeout_grace() -> None:
    assert (
        resolve_google_meet_gateway_operation_timeout_ms(
            resolve_google_meet_config({"chrome": {"joinTimeoutMs": float("inf")}})
        )
        == MAX_TIMER_TIMEOUT_MS
    )
    assert (
        resolve_google_meet_gateway_operation_timeout_ms(
            resolve_google_meet_config({"voiceCall": {"requestTimeoutMs": float("inf")}})
        )
        == MAX_TIMER_TIMEOUT_MS
    )
