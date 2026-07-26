"""Tests for Azure Speech TTS helpers."""

from __future__ import annotations

import json
from typing import Any

import pytest

from openclaw_extensions.azure_speech.tts import (
    azure_speech_tts,
    build_azure_speech_ssml,
    infer_azure_speech_file_extension,
    is_azure_speech_voice_compatible,
    list_azure_speech_voices,
    normalize_azure_speech_base_url,
)


class _StreamReader:
    def __init__(self, chunk_count: int, chunk_size: int, *, byte_value: int = 121) -> None:
        self._chunk_count = chunk_count
        self._chunk_size = chunk_size
        self._byte_value = byte_value
        self._reads = 0
        self._canceled = False

    async def read(self) -> tuple[bytes, bool]:
        if self._reads >= self._chunk_count:
            return b"", True
        self._reads += 1
        return bytes([self._byte_value]) * self._chunk_size, False

    async def cancel(self) -> None:
        self._canceled = True

    @property
    def read_count(self) -> int:
        return self._reads


class _StreamingBody:
    def __init__(self, reader: _StreamReader) -> None:
        self._reader = reader

    def get_reader(self) -> _StreamReader:
        return self._reader


class _MockResponse:
    def __init__(
        self,
        *,
        status: int = 200,
        headers: dict[str, str] | None = None,
        body: bytes | None = None,
        reader: _StreamReader | None = None,
    ) -> None:
        self.status = status
        self.status_code = status
        self.ok = 200 <= status < 300
        self.is_success = self.ok
        self.headers = headers or {}
        self.reason_phrase = "OK" if self.ok else "Error"
        self._body = body
        self._reader = reader
        self.body = _StreamingBody(reader) if reader is not None else None

    async def aread(self) -> bytes:
        if self._body is None:
            return b""
        return self._body

    def aiter_bytes(self) -> Any:
        async def _iter() -> Any:
            if self._body:
                yield self._body

        return _iter()

    async def text(self) -> str:
        raise RuntimeError("unbounded")

    async def json(self) -> Any:
        if self._body is None:
            return None
        return json.loads(self._body.decode("utf-8"))


@pytest.fixture(autouse=True)
def reset_azure_fetch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "openclaw_extensions.azure_speech.tts._default_fetch_fn",
        _missing_fetch,
    )


async def _missing_fetch(*_args: Any, **_kwargs: Any) -> Any:
    raise AssertionError("expected Azure Speech fetch to be mocked")


def _install_fetch_mock(
    monkeypatch: pytest.MonkeyPatch,
    *,
    responses: list[_MockResponse] | _MockResponse,
    calls: list[tuple[str, dict[str, Any]]] | None = None,
) -> list[tuple[str, dict[str, Any]]]:
    recorded_calls: list[tuple[str, dict[str, Any]]] = calls if calls is not None else []
    queue = [responses] if isinstance(responses, _MockResponse) else list(responses)

    async def fetch_fn(url: str, init: dict[str, Any], *, timeout_ms: int) -> _MockResponse:
        del timeout_ms
        recorded_calls.append((url, init))
        if not queue:
            raise AssertionError("unexpected Azure Speech fetch call")
        return queue.pop(0)

    monkeypatch.setattr("openclaw_extensions.azure_speech.tts._default_fetch_fn", fetch_fn)
    return recorded_calls


def test_escapes_ssml_text_and_attributes() -> None:
    assert build_azure_speech_ssml(
        text='Tom & "Jerry" <tag>',
        voice='en-US-JennyNeural" xml:lang="evil',
        lang='en-US" bad="1',
    ) == (
        '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" '
        'xml:lang="en-US&quot; bad=&quot;1">'
        '<voice name="en-US-JennyNeural&quot; xml:lang=&quot;evil">'
        'Tom &amp; "Jerry" &lt;tag&gt;</voice></speak>'
    )


def test_normalizes_region_and_endpoint_routing() -> None:
    assert normalize_azure_speech_base_url(region="eastus") == (
        "https://eastus.tts.speech.microsoft.com"
    )
    assert (
        normalize_azure_speech_base_url(
            endpoint="https://eastus.tts.speech.microsoft.com/cognitiveservices/v1/"
        )
        == "https://eastus.tts.speech.microsoft.com"
    )
    assert normalize_azure_speech_base_url(base_url="https://custom.example.com/") == (
        "https://custom.example.com"
    )


def test_maps_azure_output_formats_to_attachment_metadata() -> None:
    assert infer_azure_speech_file_extension("audio-24khz-48kbitrate-mono-mp3") == ".mp3"
    assert infer_azure_speech_file_extension("ogg-24khz-16bit-mono-opus") == ".ogg"
    assert infer_azure_speech_file_extension("riff-24khz-16bit-mono-pcm") == ".wav"
    assert infer_azure_speech_file_extension("raw-8khz-8bit-mono-mulaw") == ".pcm"
    assert is_azure_speech_voice_compatible("ogg-24khz-16bit-mono-opus") is True
    assert is_azure_speech_voice_compatible("webm-24khz-16bit-mono-opus") is False


@pytest.mark.asyncio
async def test_posts_ssml_to_the_region_endpoint_with_azure_speech_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _install_fetch_mock(
        monkeypatch,
        responses=_MockResponse(status=200, body=b"mp3"),
    )

    result = await azure_speech_tts(
        text="hello",
        api_key="speech-key",
        region="eastus",
        voice="en-US-JennyNeural",
        lang="en-US",
        output_format="audio-24khz-48kbitrate-mono-mp3",
        timeout_ms=1234,
    )

    assert result == b"mp3"
    assert len(calls) == 1
    url, init = calls[0]
    assert url == "https://eastus.tts.speech.microsoft.com/cognitiveservices/v1"
    assert init["method"] == "POST"
    assert init["headers"]["Ocp-Apim-Subscription-Key"] == "speech-key"
    assert init["headers"]["Content-Type"] == "application/ssml+xml"
    assert init["headers"]["X-Microsoft-OutputFormat"] == "audio-24khz-48kbitrate-mono-mp3"
    assert '<voice name="en-US-JennyNeural">hello</voice>' in init["body"]


@pytest.mark.asyncio
async def test_caps_streamed_audio_responses_instead_of_buffering_oversized_tts_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reader = _StreamReader(chunk_count=20, chunk_size=1024, byte_value=121)
    _install_fetch_mock(
        monkeypatch,
        responses=_MockResponse(status=200, reader=reader),
    )

    with pytest.raises(RuntimeError, match="Azure Speech TTS audio response exceeds 2048 bytes"):
        await azure_speech_tts(
            text="hello",
            api_key="speech-key",
            region="eastus",
            voice="en-US-JennyNeural",
            lang="en-US",
            output_format="audio-24khz-48kbitrate-mono-mp3",
            timeout_ms=1234,
            max_bytes=2048,
        )

    assert reader.read_count < 20


@pytest.mark.asyncio
async def test_lists_voices_with_timeout_and_filters_deprecated_entries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _install_fetch_mock(
        monkeypatch,
        responses=_MockResponse(
            status=200,
            headers={"Content-Type": "application/json"},
            body=json.dumps(
                [
                    {
                        "ShortName": "en-US-JennyNeural",
                        "DisplayName": "Jenny",
                        "Locale": "en-US",
                        "Gender": "Female",
                        "Status": "GA",
                        "VoiceTag": {"VoicePersonalities": ["Warm"]},
                    },
                    {"ShortName": "en-US-OldNeural", "DisplayName": "Old", "Status": "Deprecated"},
                    {
                        "ShortName": "en-US-RetiredNeural",
                        "DisplayName": "Retired",
                        "IsDeprecated": True,
                    },
                ]
            ).encode("utf-8"),
        ),
    )

    voices = await list_azure_speech_voices(
        api_key="speech-key",
        base_url="https://custom.example.com",
        timeout_ms=4321,
    )

    assert len(calls) == 1
    url, init = calls[0]
    assert url == "https://custom.example.com/cognitiveservices/voices/list"
    assert init["headers"]["Ocp-Apim-Subscription-Key"] == "speech-key"
    assert voices == [
        {
            "id": "en-US-JennyNeural",
            "name": "Jenny",
            "description": "Warm",
            "locale": "en-US",
            "gender": "Female",
            "personalities": ["Warm"],
        }
    ]
