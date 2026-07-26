"""Tests for the Comfy video generation provider."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock

import pytest

from openclaw.plugin_sdk.provider_test_contracts import (
    expect_explicit_video_generation_capabilities,
)
from openclaw_extensions.comfy.test_helpers import (
    build_comfy_config,
    mock_comfy_cloud_job_responses,
    mock_comfy_provider_api_key,
    parse_comfy_json_body,
)
from openclaw_extensions.comfy.video_generation_provider import (
    build_comfy_video_generation_provider,
)
from openclaw_extensions.comfy.workflow_runtime import set_comfy_fetch_guard_for_testing


class _MockResponse:
    def __init__(
        self,
        *,
        content: bytes,
        headers: dict[str, str] | None = None,
    ) -> None:
        self._content = content
        self.status = 200
        self.ok = True
        self.headers = headers or {}

    async def json(self) -> Any:
        return json.loads(self._content.decode("utf-8"))

    async def aread(self) -> bytes:
        return self._content


def _fetch_guard_result(response: _MockResponse) -> dict[str, Any]:
    return {"response": response, "release": AsyncMock()}


def _fetch_guard_params(fetch_guard_mock: AsyncMock, call: int) -> dict[str, Any]:
    return fetch_guard_mock.call_args_list[call].args[0]


@pytest.fixture
def fetch_guard_mock() -> AsyncMock:
    return AsyncMock()


@pytest.fixture(autouse=True)
def _reset_fetch_guard() -> Any:
    yield
    set_comfy_fetch_guard_for_testing(None)


def test_declares_explicit_mode_capabilities() -> None:
    expect_explicit_video_generation_capabilities(build_comfy_video_generation_provider())


def test_treats_local_comfy_video_workflows_as_configured_without_api_key() -> None:
    provider = build_comfy_video_generation_provider()
    assert provider["isConfigured"](
        {
            "cfg": build_comfy_config(
                {
                    "video": {
                        "workflow": {"6": {"inputs": {"text": ""}}},
                        "promptNodeId": "6",
                    },
                }
            ),
        }
    )


@pytest.mark.asyncio
async def test_submits_local_workflow_waits_for_history_and_downloads_videos(
    fetch_guard_mock: AsyncMock,
) -> None:
    set_comfy_fetch_guard_for_testing(fetch_guard_mock)
    fetch_guard_mock.side_effect = [
        _fetch_guard_result(
            _MockResponse(
                content=json.dumps({"prompt_id": "local-video-1"}).encode("utf-8"),
                headers={"content-type": "application/json"},
            )
        ),
        _fetch_guard_result(
            _MockResponse(
                content=json.dumps(
                    {
                        "local-video-1": {
                            "outputs": {
                                "9": {
                                    "gifs": [
                                        {
                                            "filename": "generated.mp4",
                                            "subfolder": "",
                                            "type": "output",
                                        },
                                    ],
                                },
                            },
                        },
                    }
                ).encode("utf-8"),
                headers={"content-type": "application/json"},
            )
        ),
        _fetch_guard_result(
            _MockResponse(
                content=b"mp4-data",
                headers={"content-type": "video/mp4"},
            )
        ),
    ]

    provider = build_comfy_video_generation_provider()
    result = await provider["generateVideo"](
        {
            "provider": "comfy",
            "model": "workflow",
            "prompt": "animate a lobster",
            "cfg": build_comfy_config(
                {
                    "video": {
                        "workflow": {
                            "6": {"inputs": {"text": ""}},
                            "9": {"inputs": {}},
                        },
                        "promptNodeId": "6",
                        "outputNodeId": "9",
                    },
                }
            ),
        }
    )

    assert _fetch_guard_params(fetch_guard_mock, 0)["url"] == "http://127.0.0.1:8188/prompt"
    assert _fetch_guard_params(fetch_guard_mock, 0)["auditContext"] == "comfy-video-generate"
    assert parse_comfy_json_body(fetch_guard_mock, 1) == {
        "prompt": {
            "6": {"inputs": {"text": "animate a lobster"}},
            "9": {"inputs": {}},
        },
    }
    assert _fetch_guard_params(fetch_guard_mock, 1)["url"] == (
        "http://127.0.0.1:8188/history/local-video-1"
    )
    assert _fetch_guard_params(fetch_guard_mock, 1)["auditContext"] == "comfy-history"
    assert _fetch_guard_params(fetch_guard_mock, 2)["url"] == (
        "http://127.0.0.1:8188/view?filename=generated.mp4&subfolder=&type=output"
    )
    assert _fetch_guard_params(fetch_guard_mock, 2)["auditContext"] == "comfy-video-download"
    assert result == {
        "videos": [
            {
                "buffer": b"mp4-data",
                "mimeType": "video/mp4",
                "fileName": "generated.mp4",
                "metadata": {
                    "nodeId": "9",
                    "promptId": "local-video-1",
                },
            }
        ],
        "model": "workflow",
        "metadata": {
            "promptId": "local-video-1",
            "outputNodeIds": ["9"],
        },
    }


@pytest.mark.asyncio
async def test_rejects_generated_video_downloads_that_exceed_media_cap(
    fetch_guard_mock: AsyncMock,
) -> None:
    set_comfy_fetch_guard_for_testing(fetch_guard_mock)
    fetch_guard_mock.side_effect = [
        _fetch_guard_result(
            _MockResponse(
                content=json.dumps({"prompt_id": "local-video-1"}).encode("utf-8"),
                headers={"content-type": "application/json"},
            )
        ),
        _fetch_guard_result(
            _MockResponse(
                content=json.dumps(
                    {
                        "local-video-1": {
                            "outputs": {
                                "9": {
                                    "gifs": [
                                        {
                                            "filename": "generated.mp4",
                                            "subfolder": "",
                                            "type": "output",
                                        },
                                    ],
                                },
                            },
                        },
                    }
                ).encode("utf-8"),
                headers={"content-type": "application/json"},
            )
        ),
        _fetch_guard_result(
            _MockResponse(
                content=b"too-large",
                headers={"content-type": "video/mp4"},
            )
        ),
    ]

    provider = build_comfy_video_generation_provider()
    cfg = build_comfy_config(
        {
            "video": {
                "workflow": {
                    "6": {"inputs": {"text": ""}},
                    "9": {"inputs": {}},
                },
                "promptNodeId": "6",
                "outputNodeId": "9",
            },
        }
    )
    cfg["agents"] = {"defaults": {"mediaMaxMb": 0.000001}}
    with pytest.raises(RuntimeError, match="Comfy video output download exceeds 1 bytes"):
        await provider["generateVideo"](
            {
                "provider": "comfy",
                "model": "workflow",
                "prompt": "animate a lobster",
                "cfg": cfg,
            }
        )


@pytest.mark.asyncio
async def test_uses_cloud_endpoints_for_video_workflows(fetch_guard_mock: AsyncMock) -> None:
    with mock_comfy_provider_api_key():
        set_comfy_fetch_guard_for_testing(fetch_guard_mock)
        mock_comfy_cloud_job_responses(
            fetch_guard_mock,
            body=b"cloud-video-data",
            content_type="video/mp4",
            filename="cloud.mp4",
            output_kind="gifs",
            prompt_id="cloud-video-1",
            redirect_location="https://cdn.example.com/cloud.mp4",
        )

        provider = build_comfy_video_generation_provider()
        result = await provider["generateVideo"](
            {
                "provider": "comfy",
                "model": "workflow",
                "prompt": "cloud video workflow",
                "cfg": build_comfy_config(
                    {
                        "mode": "cloud",
                        "video": {
                            "workflow": {
                                "6": {"inputs": {"text": ""}},
                                "9": {"inputs": {}},
                            },
                            "promptNodeId": "6",
                            "outputNodeId": "9",
                        },
                    }
                ),
            }
        )

    assert _fetch_guard_params(fetch_guard_mock, 0)["url"] == "https://cloud.comfy.org/api/prompt"
    assert _fetch_guard_params(fetch_guard_mock, 0)["auditContext"] == "comfy-video-generate"
    assert result["metadata"] == {
        "promptId": "cloud-video-1",
        "outputNodeIds": ["9"],
    }
