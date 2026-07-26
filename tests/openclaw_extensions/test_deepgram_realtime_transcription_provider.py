"""Tests for Deepgram realtime transcription provider plugin behavior."""

from __future__ import annotations

import pytest

from openclaw_extensions.deepgram.realtime_transcription_provider import (
    build_deepgram_realtime_transcription_provider,
    testing,
)


def test_normalizes_nested_provider_config() -> None:
    provider = build_deepgram_realtime_transcription_provider()
    resolved = provider["resolveConfig"](
        {
            "cfg": {},
            "rawConfig": {
                "providers": {
                    "deepgram": {
                        "apiKey": "dg-key",
                        "model": "nova-3",
                        "encoding": "g711_ulaw",
                        "sample_rate": "8000",
                        "interim_results": "true",
                        "endpointing": "500",
                        "language": "en-US",
                    },
                },
            },
        }
    )

    assert resolved == {
        "apiKey": "dg-key",
        "baseUrl": None,
        "model": "nova-3",
        "language": "en-US",
        "sampleRate": 8000.0,
        "encoding": "mulaw",
        "interimResults": True,
        "endpointingMs": 500.0,
    }


def test_builds_a_deepgram_listen_websocket_url() -> None:
    url = testing["toDeepgramRealtimeWsUrl"](
        {
            "apiKey": "dg-key",
            "baseUrl": "https://api.deepgram.com/v1",
            "model": "nova-3",
            "providerConfig": {},
            "sampleRate": 8000,
            "encoding": "mulaw",
            "interimResults": True,
            "endpointingMs": 800,
        }
    )

    assert "wss://api.deepgram.com/v1/listen?" in url
    assert "model=nova-3" in url
    assert "encoding=mulaw" in url
    assert "sample_rate=8000" in url


def test_requires_an_api_key_when_creating_sessions(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEPGRAM_API_KEY", "")
    provider = build_deepgram_realtime_transcription_provider()
    with pytest.raises(RuntimeError, match="Deepgram API key missing"):
        provider["createSession"]({"providerConfig": {}})
