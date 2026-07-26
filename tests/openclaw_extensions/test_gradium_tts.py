"""Tests for the Gradium TTS client."""

from __future__ import annotations

import json
from typing import Any

import pytest

from openclaw_extensions.gradium.tts import gradium_tts


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
    responses: list[_MockResponse] | _MockResponse,
    calls: list[tuple[str, dict[str, Any]]] | None = None,
) -> list[tuple[str, dict[str, Any]]]:
    recorded_calls: list[tuple[str, dict[str, Any]]] = calls if calls is not None else []
    queue = [responses] if isinstance(responses, _MockResponse) else list(responses)

    async def fetch_fn(url: str, init: dict[str, Any], *, timeout_ms: int) -> _MockResponse:
        del timeout_ms
        recorded_calls.append((url, init))
        if not queue:
            raise AssertionError("unexpected Gradium fetch call")
        return queue.pop(0)

    monkeypatch.setattr("openclaw_extensions.gradium.tts._default_fetch_fn", fetch_fn)
    return recorded_calls


@pytest.mark.asyncio
async def test_includes_parsed_provider_detail_and_request_id_for_json_api_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fetch_mock(
        monkeypatch,
        responses=_MockResponse(
            status=401,
            headers={
                "Content-Type": "application/json",
                "x-request-id": "grad_req_123",
            },
            body=json.dumps({"message": "Invalid API key"}).encode("utf-8"),
        ),
    )

    with pytest.raises(
        RuntimeError,
        match=r"Gradium API error \(401\): Invalid API key \[request_id=grad_req_123\]",
    ):
        await gradium_tts(
            text="hello",
            api_key="bad-key",
            base_url="https://api.gradium.ai",
            voice_id="YTpq7expH9539ERJ",
            output_format="wav",
            timeout_ms=5_000,
        )


@pytest.mark.asyncio
async def test_falls_back_to_raw_body_text_when_the_error_body_is_non_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fetch_mock(
        monkeypatch,
        responses=_MockResponse(status=503, body=b"service unavailable"),
    )

    with pytest.raises(RuntimeError, match=r"Gradium API error \(503\): service unavailable"):
        await gradium_tts(
            text="hello",
            api_key="test-key",
            base_url="https://api.gradium.ai",
            voice_id="YTpq7expH9539ERJ",
            output_format="wav",
            timeout_ms=5_000,
        )


@pytest.mark.asyncio
async def test_caps_streamed_non_json_error_reads_instead_of_consuming_full_response_bodies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reader = _StreamReader(chunk_count=200, chunk_size=1024, byte_value=121)
    _install_fetch_mock(
        monkeypatch,
        responses=_MockResponse(status=503, reader=reader),
    )

    with pytest.raises(RuntimeError, match=r"Gradium API error \(503\)"):
        await gradium_tts(
            text="hello",
            api_key="test-key",
            base_url="https://api.gradium.ai",
            voice_id="YTpq7expH9539ERJ",
            output_format="wav",
            timeout_ms=5_000,
        )

    assert reader.read_count < 200


@pytest.mark.asyncio
async def test_sends_the_correct_request_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    audio_data = b"fake-wav-data"
    calls = _install_fetch_mock(
        monkeypatch,
        responses=_MockResponse(status=200, body=audio_data),
    )

    result = await gradium_tts(
        text="Hello world",
        api_key="gsk_test123",
        base_url="https://api.gradium.ai",
        voice_id="YTpq7expH9539ERJ",
        output_format="wav",
        timeout_ms=5_000,
    )

    assert len(calls) == 1
    url, init = calls[0]
    assert url == "https://api.gradium.ai/api/post/speech/tts"
    assert init["method"] == "POST"
    assert init["headers"]["x-api-key"] == "gsk_test123"
    assert init["headers"]["Content-Type"] == "application/json"
    assert json.loads(init["body"]) == {
        "text": "Hello world",
        "voice_id": "YTpq7expH9539ERJ",
        "only_audio": True,
        "output_format": "wav",
        "json_config": '{"padding_bonus":0}',
    }
    assert result == audio_data


@pytest.mark.asyncio
async def test_caps_streamed_audio_responses_instead_of_buffering_oversized_tts_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reader = _StreamReader(chunk_count=20, chunk_size=1024, byte_value=121)
    _install_fetch_mock(
        monkeypatch,
        responses=_MockResponse(status=200, reader=reader),
    )

    with pytest.raises(RuntimeError, match="Gradium TTS audio response exceeds 2048 bytes"):
        await gradium_tts(
            text="hello",
            api_key="test-key",
            base_url="https://api.gradium.ai",
            voice_id="YTpq7expH9539ERJ",
            output_format="wav",
            timeout_ms=5_000,
            max_bytes=2048,
        )

    assert reader.read_count < 20
