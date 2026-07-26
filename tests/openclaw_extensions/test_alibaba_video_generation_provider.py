"""Tests for the Alibaba video generation provider."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from openclaw.plugin_sdk.provider_test_contracts import (
    expect_dashscope_video_task_poll,
    expect_explicit_video_generation_capabilities,
    expect_successful_dashscope_video_result,
    mock_successful_dashscope_video_task,
)
from openclaw_extensions.alibaba.video_generation_provider import (
    build_alibaba_video_generation_provider,
)


@pytest.fixture
def provider_http_mocks(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Install shared provider HTTP mocks used by DashScope video provider tests."""
    from openclaw.video_generation import dashscope_compatible

    post_json_request_mock = AsyncMock()
    fetch_with_timeout_mock = AsyncMock()
    resolve_api_key_for_provider_mock = AsyncMock(return_value={"apiKey": "provider-key"})

    monkeypatch.setattr(
        dashscope_compatible,
        "post_json_request",
        post_json_request_mock,
    )
    monkeypatch.setattr(
        "openclaw.plugin_sdk.provider_http.fetch_with_timeout",
        fetch_with_timeout_mock,
    )
    monkeypatch.setattr(
        "openclaw_extensions.alibaba.video_generation_provider.resolve_api_key_for_provider",
        resolve_api_key_for_provider_mock,
    )
    return {
        "postJsonRequestMock": post_json_request_mock,
        "fetchWithTimeoutMock": fetch_with_timeout_mock,
        "resolveApiKeyForProviderMock": resolve_api_key_for_provider_mock,
    }


def _require_record(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        msg = f"expected {label} to be a record"
        raise TypeError(msg)
    return value


def _require_first_post_json_request(mocks: dict[str, Any], label: str) -> dict[str, Any]:
    if not mocks["postJsonRequestMock"].await_args_list:
        raise AssertionError(f"expected {label}")
    call = mocks["postJsonRequestMock"].await_args_list[0]
    payload = call.kwargs if call.kwargs else {"body": call.args[0] if call.args else {}}
    if "url" not in payload and call.args:
        return _require_record(call.args[0], label)
    return payload


def test_declares_explicit_mode_capabilities() -> None:
    expect_explicit_video_generation_capabilities(build_alibaba_video_generation_provider())


@pytest.mark.asyncio
async def test_submits_async_wan_generation_polls_and_downloads(
    provider_http_mocks: dict[str, Any],
) -> None:
    mock_successful_dashscope_video_task(provider_http_mocks)

    provider = build_alibaba_video_generation_provider()
    result = await provider["generateVideo"](
        {
            "provider": "alibaba",
            "model": "wan2.6-r2v-flash",
            "prompt": "animate this shot",
            "cfg": {},
            "inputImages": [{"url": "https://example.com/ref.png"}],
            "durationSeconds": 6,
            "audio": True,
            "watermark": False,
        }
    )

    assert provider_http_mocks["postJsonRequestMock"].await_count == 1
    request = _require_first_post_json_request(provider_http_mocks, "DashScope request")
    assert request["url"] == (
        "https://dashscope-intl.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis"
    )
    body = _require_record(request["body"], "DashScope request body")
    assert body["model"] == "wan2.6-r2v-flash"
    input_payload = _require_record(body["input"], "DashScope request input")
    assert input_payload["prompt"] == "animate this shot"
    assert input_payload["img_url"] == "https://example.com/ref.png"
    parameters = _require_record(body["parameters"], "DashScope request parameters")
    assert parameters["duration"] == 6
    assert parameters["enable_audio"] is True
    assert parameters["watermark"] is False
    expect_dashscope_video_task_poll(provider_http_mocks["fetchWithTimeoutMock"])
    expect_successful_dashscope_video_result(result)


@pytest.mark.asyncio
async def test_fails_fast_for_local_buffer_reference_inputs(
    provider_http_mocks: dict[str, Any],
) -> None:
    provider = build_alibaba_video_generation_provider()

    with pytest.raises(
        ValueError,
        match=(
            "Alibaba Wan video generation currently requires remote http\\(s\\) URLs "
            "for reference images/videos\\."
        ),
    ):
        await provider["generateVideo"](
            {
                "provider": "alibaba",
                "model": "wan2.6-i2v",
                "prompt": "animate this local frame",
                "cfg": {},
                "inputImages": [{"buffer": b"png-bytes", "mimeType": "image/png"}],
            }
        )

    assert provider_http_mocks["postJsonRequestMock"].await_count == 0
