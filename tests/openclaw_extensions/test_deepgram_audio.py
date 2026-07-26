"""Tests for Deepgram audio transcription."""

from __future__ import annotations

import json
from typing import Any

import pytest

from openclaw_extensions.deepgram.audio import transcribe_deepgram_audio


class _MockResponse:
    def __init__(self, *, status: int = 200, body: Any = None, text: str | None = None) -> None:
        self.ok = 200 <= status < 300
        self.status = status
        self._body = body
        self._text = text

    async def json(self) -> Any:
        if self._body is not None:
            return self._body
        if self._text is not None:
            return json.loads(self._text)
        raise ValueError("no body")


def _create_auth_capture_json_fetch(response_body: Any) -> dict[str, Any]:
    seen_auth: dict[str, str | None] = {"value": None}

    async def fetch_fn(_url: str, init: dict[str, Any]) -> _MockResponse:
        headers = init.get("headers") or {}
        if isinstance(headers, dict):
            seen_auth["value"] = headers.get("authorization")
        return _MockResponse(body=response_body)

    return {
        "fetchFn": fetch_fn,
        "getAuthHeader": lambda: seen_auth["value"],
    }


def _create_request_capture_json_fetch(response_body: Any) -> dict[str, Any]:
    seen: dict[str, Any] = {"url": None, "init": None}

    async def fetch_fn(url: str, init: dict[str, Any]) -> _MockResponse:
        seen["url"] = url
        seen["init"] = init
        return _MockResponse(body=response_body)

    return {
        "fetchFn": fetch_fn,
        "getRequest": lambda: {"url": seen["url"], "init": seen["init"]},
    }


@pytest.mark.asyncio
async def test_respects_lowercase_authorization_header_overrides() -> None:
    capture = _create_auth_capture_json_fetch(
        {"results": {"channels": [{"alternatives": [{"transcript": "ok"}]}]}}
    )

    result = await transcribe_deepgram_audio(
        {
            "buffer": b"audio",
            "fileName": "note.mp3",
            "apiKey": "test-key",
            "timeoutMs": 1000,
            "headers": {"authorization": "Token override"},
            "fetchFn": capture["fetchFn"],
        }
    )

    assert capture["getAuthHeader"]() == "Token override"
    assert result["text"] == "ok"


@pytest.mark.asyncio
async def test_builds_the_expected_request_payload() -> None:
    capture = _create_request_capture_json_fetch(
        {"results": {"channels": [{"alternatives": [{"transcript": "hello"}]}]}}
    )

    result = await transcribe_deepgram_audio(
        {
            "buffer": b"audio-bytes",
            "fileName": "voice.wav",
            "apiKey": "test-key",
            "timeoutMs": 1234,
            "baseUrl": "https://api.example.com/v1/",
            "model": " ",
            "language": " en ",
            "mime": "audio/wav",
            "headers": {"X-Custom": "1"},
            "query": {
                "punctuate": False,
                "smart_format": True,
            },
            "fetchFn": capture["fetchFn"],
        }
    )
    request = capture["getRequest"]()
    seen_url = request["url"]
    seen_init = request["init"]

    assert result["model"] == "nova-3"
    assert result["text"] == "hello"
    assert (
        seen_url
        == "https://api.example.com/v1/listen?model=nova-3&language=en&punctuate=false&smart_format=true"
    )
    assert seen_init is not None
    assert seen_init["method"] == "POST"
    assert "timeoutMs" in seen_init
    headers = seen_init["headers"]
    assert headers["authorization"] == "Token test-key"
    assert headers["X-Custom"] == "1"
    assert headers["content-type"] == "audio/wav"
    assert isinstance(seen_init["body"], (bytes, bytearray))


@pytest.mark.asyncio
async def test_throws_when_the_provider_response_omits_transcript() -> None:
    capture = _create_request_capture_json_fetch(
        {"results": {"channels": [{"alternatives": [{}]}]}}
    )

    with pytest.raises(RuntimeError, match="Audio transcription response missing transcript"):
        await transcribe_deepgram_audio(
            {
                "buffer": b"audio-bytes",
                "fileName": "voice.wav",
                "apiKey": "test-key",
                "timeoutMs": 1234,
                "fetchFn": capture["fetchFn"],
            }
        )


@pytest.mark.asyncio
async def test_wraps_malformed_successful_transcription_json_with_stable_provider_error() -> None:
    async def fetch_fn(_url: str, _init: dict[str, Any]) -> _MockResponse:
        return _MockResponse(text="{ nope")

    with pytest.raises(Exception, match="Audio transcription failed: malformed JSON response"):
        await transcribe_deepgram_audio(
            {
                "buffer": b"audio-bytes",
                "fileName": "voice.wav",
                "apiKey": "test-key",
                "timeoutMs": 1234,
                "fetchFn": fetch_fn,
            }
        )


@pytest.mark.asyncio
async def test_rejects_non_object_successful_transcription_json_with_stable_provider_error() -> (
    None
):
    async def fetch_fn(_url: str, _init: dict[str, Any]) -> _MockResponse:
        return _MockResponse(body=[])

    with pytest.raises(Exception, match="Audio transcription failed: malformed JSON response"):
        await transcribe_deepgram_audio(
            {
                "buffer": b"audio-bytes",
                "fileName": "voice.wav",
                "apiKey": "test-key",
                "timeoutMs": 1234,
                "fetchFn": fetch_fn,
            }
        )


@pytest.mark.asyncio
async def test_rejects_wrong_nested_transcript_shapes_with_stable_provider_error() -> None:
    capture = _create_request_capture_json_fetch(
        {"results": {"channels": {"alternatives": [{"transcript": "hello"}]}}}
    )

    with pytest.raises(Exception, match="Audio transcription failed: malformed JSON response"):
        await transcribe_deepgram_audio(
            {
                "buffer": b"audio-bytes",
                "fileName": "voice.wav",
                "apiKey": "test-key",
                "timeoutMs": 1234,
                "fetchFn": capture["fetchFn"],
            }
        )


@pytest.mark.asyncio
async def test_rejects_non_string_transcript_values_with_stable_provider_error() -> None:
    capture = _create_request_capture_json_fetch(
        {"results": {"channels": [{"alternatives": [{"transcript": 123}]}]}}
    )

    with pytest.raises(Exception, match="Audio transcription failed: malformed JSON response"):
        await transcribe_deepgram_audio(
            {
                "buffer": b"audio-bytes",
                "fileName": "voice.wav",
                "apiKey": "test-key",
                "timeoutMs": 1234,
                "fetchFn": capture["fetchFn"],
            }
        )
