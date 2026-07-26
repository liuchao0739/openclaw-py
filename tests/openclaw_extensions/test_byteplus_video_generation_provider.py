"""Tests for the BytePlus video generation provider."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock

import pytest

from openclaw.plugin_sdk.provider_test_contracts import (
    expect_explicit_video_generation_capabilities,
)
from openclaw_extensions.byteplus.video_generation_provider import (
    PROVIDER_JSON_RESPONSE_MAX_BYTES,
    build_byte_plus_video_generation_provider,
)


class _StreamReader:
    def __init__(self, chunk_count: int, chunk_size: int, *, text: str = "a") -> None:
        self._chunk_count = chunk_count
        self._chunk_size = chunk_size
        self._text = text
        self._reads = 0
        self._bytes_pulled = 0
        self._canceled = False

    async def read(self) -> tuple[bytes, bool]:
        if self._reads >= self._chunk_count:
            return b"", True
        self._reads += 1
        chunk = (self._text * self._chunk_size).encode("utf-8")
        self._bytes_pulled += len(chunk)
        return chunk, False

    async def cancel(self) -> None:
        self._canceled = True


class _StreamingBody:
    def __init__(self, reader: _StreamReader) -> None:
        self._reader = reader

    def get_reader(self) -> _StreamReader:
        return self._reader


class _StreamingResponse:
    def __init__(
        self,
        reader: _StreamReader,
        *,
        status: int = 200,
        headers: dict[str, str] | None = None,
        ok: bool = True,
    ) -> None:
        self.body = _StreamingBody(reader)
        self._reader = reader
        self.status = status
        self.ok = ok
        self.headers = headers or {"content-type": "application/json"}

    async def text(self) -> str:
        raise RuntimeError("unbounded")

    async def aread(self) -> bytes:
        raise RuntimeError("unbounded")


class _SimpleResponse:
    def __init__(
        self,
        *,
        content: bytes,
        headers: dict[str, str] | None = None,
        ok: bool = True,
        status: int = 200,
    ) -> None:
        self._content = content
        self.headers = headers or {}
        self.ok = ok
        self.status = status

    async def aread(self) -> bytes:
        return self._content


def _streamed_json_response(payload: Any) -> _StreamingResponse:
    reader = _StreamReader(1, 1, text=json.dumps(payload))
    return _StreamingResponse(reader)


def _streamed_video_response(text: str) -> _StreamingResponse:
    reader = _StreamReader(1, 1, text=text)
    return _StreamingResponse(
        reader,
        headers={"content-type": "video/mp4"},
    )


def _make_oversized_json_stream() -> dict[str, Any]:
    one_mib = 1024 * 1024
    total_chunks = 32
    reader = _StreamReader(total_chunks, one_mib)
    return {
        "response": _StreamingResponse(reader),
        "max_bytes": PROVIDER_JSON_RESPONSE_MAX_BYTES,
        "total_bytes": total_chunks * one_mib,
        "state": reader,
    }


@pytest.fixture
def provider_http_mocks(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    post_json_request_mock = AsyncMock()
    fetch_with_timeout_mock = AsyncMock()
    resolve_api_key_for_provider_mock = AsyncMock(return_value={"apiKey": "provider-key"})

    async def fetch_provider_operation_response(params: dict[str, Any]) -> Any:
        timeout_ms = params.get("timeoutMs")
        resolved_timeout = timeout_ms() if callable(timeout_ms) else (timeout_ms or 60_000)
        return await fetch_with_timeout_mock(
            params["url"],
            params.get("init") or {},
            resolved_timeout,
        )

    async def fetch_provider_download_response(params: dict[str, Any]) -> Any:
        timeout_ms = params.get("timeoutMs")
        resolved_timeout = timeout_ms() if callable(timeout_ms) else (timeout_ms or 60_000)
        return await fetch_with_timeout_mock(
            params["url"],
            params.get("init") or {},
            resolved_timeout,
        )

    monkeypatch.setattr(
        "openclaw_extensions.byteplus.video_generation_provider.post_json_request",
        post_json_request_mock,
    )
    monkeypatch.setattr(
        "openclaw_extensions.byteplus.video_generation_provider.fetch_provider_operation_response",
        fetch_provider_operation_response,
    )
    monkeypatch.setattr(
        "openclaw_extensions.byteplus.video_generation_provider.fetch_provider_download_response",
        fetch_provider_download_response,
    )
    monkeypatch.setattr(
        "openclaw_extensions.byteplus.video_generation_provider.resolve_api_key_for_provider",
        resolve_api_key_for_provider_mock,
    )
    return {
        "postJsonRequestMock": post_json_request_mock,
        "fetchWithTimeoutMock": fetch_with_timeout_mock,
        "resolveApiKeyForProviderMock": resolve_api_key_for_provider_mock,
    }


def _require_byteplus_post_request(mocks: dict[str, Any]) -> dict[str, Any]:
    if not mocks["postJsonRequestMock"].await_args_list:
        raise AssertionError("expected BytePlus video request")
    call = mocks["postJsonRequestMock"].await_args_list[0]
    if call.kwargs:
        return call.kwargs
    if call.args:
        return call.args[0]
    raise AssertionError("expected BytePlus video request")


def _require_byteplus_post_body(mocks: dict[str, Any]) -> dict[str, Any]:
    request = _require_byteplus_post_request(mocks)
    body = request.get("body")
    if not isinstance(body, dict):
        msg = "expected BytePlus video request body"
        raise TypeError(msg)
    return body


def _mock_successful_byteplus_task(
    mocks: dict[str, Any],
    *,
    model: str = "seedance-1-0-lite-t2v-250428",
) -> None:
    mocks["postJsonRequestMock"].return_value = {
        "response": _streamed_json_response({"id": "task_123"}),
        "release": AsyncMock(),
    }
    mocks["fetchWithTimeoutMock"].side_effect = [
        _streamed_json_response(
            {
                "id": "task_123",
                "status": "succeeded",
                "content": {
                    "video_url": "https://example.com/byteplus.mp4",
                },
                "model": model,
            }
        ),
        _SimpleResponse(
            content=b"webm-bytes",
            headers={"content-type": "video/webm"},
        ),
    ]


def test_declares_explicit_mode_capabilities() -> None:
    expect_explicit_video_generation_capabilities(build_byte_plus_video_generation_provider())


@pytest.mark.asyncio
async def test_creates_a_content_generation_task_polls_and_downloads(
    provider_http_mocks: dict[str, Any],
) -> None:
    _mock_successful_byteplus_task(provider_http_mocks)

    provider = build_byte_plus_video_generation_provider()
    result = await provider["generateVideo"](
        {
            "provider": "byteplus",
            "model": "seedance-1-0-lite-t2v-250428",
            "prompt": "A lantern floats upward into the night sky",
            "cfg": {},
        }
    )

    assert provider_http_mocks["postJsonRequestMock"].await_count == 1
    request = _require_byteplus_post_request(provider_http_mocks)
    assert request["url"] == (
        "https://ark.ap-southeast.bytepluses.com/api/v3/contents/generations/tasks"
    )
    assert len(result["videos"]) == 1
    assert result["videos"][0]["fileName"] == "video-1.webm"
    assert result["metadata"]["taskId"] == "task_123"


@pytest.mark.asyncio
async def test_rejects_generated_video_downloads_that_exceed_the_configured_media_cap(
    provider_http_mocks: dict[str, Any],
) -> None:
    provider_http_mocks["postJsonRequestMock"].return_value = {
        "response": _streamed_json_response({"id": "task_too_large"}),
        "release": AsyncMock(),
    }
    provider_http_mocks["fetchWithTimeoutMock"].side_effect = [
        _streamed_json_response(
            {
                "id": "task_too_large",
                "status": "succeeded",
                "content": {
                    "video_url": "https://example.com/too-large.mp4",
                },
            }
        ),
        _streamed_video_response("too-large"),
    ]

    provider = build_byte_plus_video_generation_provider()
    with pytest.raises(RuntimeError, match="BytePlus generated video download exceeds 1 bytes"):
        await provider["generateVideo"](
            {
                "provider": "byteplus",
                "model": "seedance-1-0-lite-t2v-250428",
                "prompt": "short video",
                "cfg": {"agents": {"defaults": {"mediaMaxMb": 0.000001}}},
            }
        )


@pytest.mark.asyncio
async def test_switches_t2v_image_requests_to_i2v_models_and_lowercases_resolution(
    provider_http_mocks: dict[str, Any],
) -> None:
    _mock_successful_byteplus_task(
        provider_http_mocks,
        model="seedance-1-0-lite-i2v-250428",
    )

    provider = build_byte_plus_video_generation_provider()
    await provider["generateVideo"](
        {
            "provider": "byteplus",
            "model": "seedance-1-0-lite-t2v-250428",
            "prompt": "Animate this still image",
            "resolution": "720P",
            "inputImages": [{"url": "https://example.com/first-frame.png"}],
            "cfg": {},
        }
    )

    assert _require_byteplus_post_body(provider_http_mocks) == {
        "model": "seedance-1-0-lite-i2v-250428",
        "resolution": "720p",
        "content": [
            {"type": "text", "text": "Animate this still image"},
            {
                "type": "image_url",
                "image_url": {"url": "https://example.com/first-frame.png"},
                "role": "first_frame",
            },
        ],
    }


@pytest.mark.asyncio
async def test_maps_declared_provider_options_into_the_request_body(
    provider_http_mocks: dict[str, Any],
) -> None:
    _mock_successful_byteplus_task(
        provider_http_mocks,
        model="seedance-1-0-pro-250528",
    )

    provider = build_byte_plus_video_generation_provider()
    await provider["generateVideo"](
        {
            "provider": "byteplus",
            "model": "seedance-1-0-pro-250528",
            "prompt": "A cinematic lobster montage",
            "providerOptions": {
                "seed": 42,
                "draft": True,
                "camera_fixed": False,
            },
            "cfg": {},
        }
    )

    body = _require_byteplus_post_body(provider_http_mocks)
    assert body["model"] == "seedance-1-0-pro-250528"
    assert body["seed"] == 42
    assert body["resolution"] == "480p"
    assert body["camera_fixed"] is False


@pytest.mark.asyncio
async def test_drops_malformed_seed_values_before_creating_videos(
    provider_http_mocks: dict[str, Any],
) -> None:
    _mock_successful_byteplus_task(
        provider_http_mocks,
        model="seedance-1-0-pro-250528",
    )

    provider = build_byte_plus_video_generation_provider()
    await provider["generateVideo"](
        {
            "provider": "byteplus",
            "model": "seedance-1-0-pro-250528",
            "prompt": "A cinematic lobster montage",
            "providerOptions": {
                "seed": 1.5,
            },
            "cfg": {},
        }
    )

    assert "seed" not in _require_byteplus_post_body(provider_http_mocks)


@pytest.mark.asyncio
async def test_drops_out_of_range_duration_values_before_creating_videos(
    provider_http_mocks: dict[str, Any],
) -> None:
    _mock_successful_byteplus_task(
        provider_http_mocks,
        model="seedance-1-0-pro-250528",
    )

    provider = build_byte_plus_video_generation_provider()
    await provider["generateVideo"](
        {
            "provider": "byteplus",
            "model": "seedance-1-0-pro-250528",
            "prompt": "A cinematic lobster montage",
            "durationSeconds": 99,
            "cfg": {},
        }
    )

    assert "duration" not in _require_byteplus_post_body(provider_http_mocks)


@pytest.mark.asyncio
async def test_drops_malformed_response_duration_metadata(
    provider_http_mocks: dict[str, Any],
) -> None:
    provider_http_mocks["postJsonRequestMock"].return_value = {
        "response": _streamed_json_response({"id": "task_123"}),
        "release": AsyncMock(),
    }
    provider_http_mocks["fetchWithTimeoutMock"].side_effect = [
        _streamed_json_response(
            {
                "id": "task_123",
                "status": "succeeded",
                "content": {
                    "video_url": "https://example.com/byteplus.mp4",
                },
                "duration": 1.5,
            }
        ),
        _SimpleResponse(
            content=b"mp4-bytes",
            headers={"content-type": "video/mp4"},
        ),
    ]

    provider = build_byte_plus_video_generation_provider()
    result = await provider["generateVideo"](
        {
            "provider": "byteplus",
            "model": "seedance-1-0-lite-t2v-250428",
            "prompt": "A lantern floats upward into the night sky",
            "cfg": {},
        }
    )

    assert result["metadata"]["duration"] is None


@pytest.mark.asyncio
async def test_reports_malformed_create_json_with_a_provider_owned_error(
    provider_http_mocks: dict[str, Any],
) -> None:
    release = AsyncMock()
    provider_http_mocks["postJsonRequestMock"].return_value = {
        "response": _StreamingResponse(
            _StreamReader(1, 16, text="{ not valid json"),
        ),
        "release": release,
    }

    provider = build_byte_plus_video_generation_provider()
    with pytest.raises(
        RuntimeError, match="BytePlus video generation failed: malformed JSON response"
    ):
        await provider["generateVideo"](
            {
                "provider": "byteplus",
                "model": "seedance-1-0-lite-t2v-250428",
                "prompt": "bad create response",
                "cfg": {},
            }
        )
    release.assert_awaited_once()


@pytest.mark.asyncio
async def test_rejects_status_responses_missing_a_task_status(
    provider_http_mocks: dict[str, Any],
) -> None:
    provider_http_mocks["postJsonRequestMock"].return_value = {
        "response": _streamed_json_response({"id": "task_missing_status"}),
        "release": AsyncMock(),
    }
    provider_http_mocks["fetchWithTimeoutMock"].return_value = _streamed_json_response(
        {
            "id": "task_missing_status",
            "content": {
                "video_url": "https://example.com/byteplus.mp4",
            },
        }
    )

    provider = build_byte_plus_video_generation_provider()
    with pytest.raises(ValueError, match="BytePlus video status response missing task status"):
        await provider["generateVideo"](
            {
                "provider": "byteplus",
                "model": "seedance-1-0-lite-t2v-250428",
                "prompt": "missing status",
                "cfg": {},
            }
        )


@pytest.mark.asyncio
async def test_rejects_malformed_completed_content(
    provider_http_mocks: dict[str, Any],
) -> None:
    provider_http_mocks["postJsonRequestMock"].return_value = {
        "response": _streamed_json_response({"id": "task_malformed_content"}),
        "release": AsyncMock(),
    }
    provider_http_mocks["fetchWithTimeoutMock"].return_value = _streamed_json_response(
        {
            "id": "task_malformed_content",
            "status": "succeeded",
            "content": ["https://example.com/byteplus.mp4"],
        }
    )

    provider = build_byte_plus_video_generation_provider()
    with pytest.raises(
        ValueError,
        match="BytePlus video generation completed with malformed content",
    ):
        await provider["generateVideo"](
            {
                "provider": "byteplus",
                "model": "seedance-1-0-lite-t2v-250428",
                "prompt": "malformed content",
                "cfg": {},
            }
        )


@pytest.mark.asyncio
async def test_bounds_the_submit_task_json_body_and_cancels_an_oversized_stream(
    provider_http_mocks: dict[str, Any],
) -> None:
    stream = _make_oversized_json_stream()
    release = AsyncMock()
    provider_http_mocks["postJsonRequestMock"].return_value = {
        "response": stream["response"],
        "release": release,
    }

    provider = build_byte_plus_video_generation_provider()
    with pytest.raises(
        RuntimeError,
        match=(
            f"BytePlus video generation failed: JSON response exceeds {stream['max_bytes']} bytes"
        ),
    ):
        await provider["generateVideo"](
            {
                "provider": "byteplus",
                "model": "seedance-1-0-lite-t2v-250428",
                "prompt": "oversized submit response",
                "cfg": {},
            }
        )
    assert stream["state"]._canceled is True
    assert stream["state"]._bytes_pulled < stream["total_bytes"]
    release.assert_awaited_once()


@pytest.mark.asyncio
async def test_bounds_the_poll_status_json_body_and_cancels_an_oversized_stream(
    provider_http_mocks: dict[str, Any],
) -> None:
    provider_http_mocks["postJsonRequestMock"].return_value = {
        "response": _streamed_json_response({"id": "task_oversized_poll"}),
        "release": AsyncMock(),
    }
    stream = _make_oversized_json_stream()
    provider_http_mocks["fetchWithTimeoutMock"].return_value = stream["response"]

    provider = build_byte_plus_video_generation_provider()
    with pytest.raises(
        RuntimeError,
        match=(
            f"BytePlus video status request failed: JSON response exceeds {stream['max_bytes']} bytes"
        ),
    ):
        await provider["generateVideo"](
            {
                "provider": "byteplus",
                "model": "seedance-1-0-lite-t2v-250428",
                "prompt": "oversized poll response",
                "cfg": {},
            }
        )
    assert stream["state"]._canceled is True
    assert stream["state"]._bytes_pulled < stream["total_bytes"]
