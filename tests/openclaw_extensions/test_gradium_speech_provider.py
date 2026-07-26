"""Tests for the Gradium speech provider."""

from __future__ import annotations

import json
import os
from typing import Any

import pytest

from openclaw_extensions.gradium.speech_provider import build_gradium_speech_provider


class _MockResponse:
    def __init__(self, *, status: int = 200, body: bytes | None = None) -> None:
        self.status = status
        self.status_code = status
        self.ok = 200 <= status < 300
        self.is_success = self.ok
        self.headers: dict[str, str] = {}
        self.reason_phrase = "OK" if self.ok else "Error"
        self._body = body or b""
        self.body = None

    async def aread(self) -> bytes:
        return self._body

    def aiter_bytes(self) -> Any:
        async def _iter() -> Any:
            if self._body:
                yield self._body

        return _iter()


@pytest.fixture
def provider() -> dict[str, Any]:
    return build_gradium_speech_provider()


@pytest.fixture(autouse=True)
def reset_gradium_fetch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "openclaw_extensions.gradium.tts._default_fetch_fn",
        _missing_fetch,
    )


async def _missing_fetch(*_args: Any, **_kwargs: Any) -> Any:
    raise AssertionError("expected Gradium fetch to be mocked")


def _install_fetch_mock(
    monkeypatch: pytest.MonkeyPatch,
    *,
    body: bytes,
) -> list[tuple[str, dict[str, Any]]]:
    calls: list[tuple[str, dict[str, Any]]] = []

    async def fetch_fn(url: str, init: dict[str, Any], *, timeout_ms: int) -> _MockResponse:
        del timeout_ms
        calls.append((url, init))
        return _MockResponse(status=200, body=body)

    monkeypatch.setattr("openclaw_extensions.gradium.tts._default_fetch_fn", fetch_fn)
    return calls


def test_reports_configured_when_gradium_api_key_is_set(provider: dict[str, Any]) -> None:
    original = os.environ.get("GRADIUM_API_KEY")
    try:
        os.environ["GRADIUM_API_KEY"] = "gsk_test"
        assert provider["isConfigured"]({"providerConfig": {}, "timeoutMs": 5_000}) is True
    finally:
        if original is None:
            os.environ.pop("GRADIUM_API_KEY", None)
        else:
            os.environ["GRADIUM_API_KEY"] = original


def test_reports_not_configured_when_no_key_is_available(provider: dict[str, Any]) -> None:
    original = os.environ.get("GRADIUM_API_KEY")
    try:
        os.environ.pop("GRADIUM_API_KEY", None)
        assert provider["isConfigured"]({"providerConfig": {}, "timeoutMs": 5_000}) is False
    finally:
        if original is not None:
            os.environ["GRADIUM_API_KEY"] = original


@pytest.mark.asyncio
async def test_synthesizes_audio_via_the_gradium_tts_endpoint(
    provider: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audio_data = b"wav-audio-data"
    calls = _install_fetch_mock(monkeypatch, body=audio_data)

    result = await provider["synthesize"](
        {
            "text": "OpenClaw test",
            "cfg": {},
            "providerConfig": {"apiKey": "gsk_test123"},
            "target": "audio-file",
            "timeoutMs": 30_000,
        }
    )

    assert len(calls) == 1
    url, init = calls[0]
    assert url == "https://api.gradium.ai/api/post/speech/tts"
    assert init["headers"]["x-api-key"] == "gsk_test123"
    assert json.loads(init["body"]) == {
        "text": "OpenClaw test",
        "voice_id": "YTpq7expH9539ERJ",
        "only_audio": True,
        "output_format": "wav",
        "json_config": '{"padding_bonus":0}',
    }
    assert result["outputFormat"] == "wav"
    assert result["fileExtension"] == ".wav"
    assert result["voiceCompatible"] is False
    assert result["audioBuffer"] == audio_data


@pytest.mark.asyncio
async def test_uses_opus_and_voice_compatible_for_voice_note_target(
    provider: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audio_data = b"opus-audio-data"
    calls = _install_fetch_mock(monkeypatch, body=audio_data)

    result = await provider["synthesize"](
        {
            "text": "Voice note test",
            "cfg": {},
            "providerConfig": {"apiKey": "gsk_test123"},
            "target": "voice-note",
            "timeoutMs": 30_000,
        }
    )

    assert json.loads(calls[0][1]["body"])["output_format"] == "opus"
    assert result["outputFormat"] == "opus"
    assert result["fileExtension"] == ".opus"
    assert result["voiceCompatible"] is True
    assert result["audioBuffer"] == audio_data


@pytest.mark.asyncio
async def test_applies_the_configured_media_byte_cap_to_synthesized_audio(
    provider: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fetch_fn(url: str, init: dict[str, Any], *, timeout_ms: int) -> _MockResponse:
        del url, init, timeout_ms
        return _MockResponse(status=200, body=bytes(2048))

    monkeypatch.setattr("openclaw_extensions.gradium.tts._default_fetch_fn", fetch_fn)

    with pytest.raises(RuntimeError, match="Gradium TTS audio response exceeds"):
        await provider["synthesize"](
            {
                "text": "OpenClaw test",
                "cfg": {"agents": {"defaults": {"mediaMaxMb": 0.001}}},
                "providerConfig": {"apiKey": "gsk_test123"},
                "target": "audio-file",
                "timeoutMs": 30_000,
            }
        )


@pytest.mark.asyncio
async def test_uses_ulaw_8000_for_telephony_synthesis(
    provider: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audio_data = b"ulaw-audio-data"
    calls = _install_fetch_mock(monkeypatch, body=audio_data)
    synthesize_telephony = provider.get("synthesizeTelephony")
    assert callable(synthesize_telephony)

    result = await synthesize_telephony(
        {
            "text": "Telephony test",
            "cfg": {},
            "providerConfig": {"apiKey": "gsk_test123", "voiceId": "default-voice"},
            "providerOverrides": {"voiceId": "override-voice"},
            "timeoutMs": 30_000,
        }
    )

    assert json.loads(calls[0][1]["body"]) == {
        "text": "Telephony test",
        "voice_id": "override-voice",
        "only_audio": True,
        "output_format": "ulaw_8000",
        "json_config": '{"padding_bonus":0}',
    }
    assert result["outputFormat"] == "ulaw_8000"
    assert result["sampleRate"] == 8_000
    assert result["audioBuffer"] == audio_data


@pytest.mark.asyncio
async def test_throws_when_no_api_key_is_available(
    provider: dict[str, Any],
) -> None:
    original = os.environ.get("GRADIUM_API_KEY")
    try:
        os.environ.pop("GRADIUM_API_KEY", None)
        with pytest.raises(RuntimeError, match="Gradium API key missing"):
            await provider["synthesize"](
                {
                    "text": "test",
                    "cfg": {},
                    "providerConfig": {},
                    "target": "audio-file",
                    "timeoutMs": 5_000,
                }
            )
    finally:
        if original is not None:
            os.environ["GRADIUM_API_KEY"] = original
