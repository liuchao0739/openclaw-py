"""Tests for the Comfy music generation provider."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock

import pytest

from openclaw_extensions.comfy.music_generation_provider import (
    build_comfy_music_generation_provider,
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


@pytest.fixture
def fetch_guard_mock() -> AsyncMock:
    return AsyncMock()


@pytest.fixture(autouse=True)
def _reset_fetch_guard() -> Any:
    yield
    set_comfy_fetch_guard_for_testing(None)


def test_registers_the_workflow_model() -> None:
    provider = build_comfy_music_generation_provider()
    assert provider["defaultModel"] == "workflow"
    assert provider["models"] == ["workflow"]
    capabilities = provider["capabilities"]
    assert capabilities.get("generate") is not None
    assert capabilities.get("edit") is not None
    edit = capabilities.get("edit") or {}
    assert edit.get("enabled") is True
    assert (edit.get("maxInputImages") or 0) > 0


@pytest.mark.asyncio
async def test_runs_music_workflow_and_returns_audio_outputs(fetch_guard_mock: AsyncMock) -> None:
    set_comfy_fetch_guard_for_testing(fetch_guard_mock)
    fetch_guard_mock.side_effect = [
        _fetch_guard_result(
            _MockResponse(
                content=json.dumps({"prompt_id": "music-job-1"}).encode("utf-8"),
                headers={"content-type": "application/json"},
            )
        ),
        _fetch_guard_result(
            _MockResponse(
                content=json.dumps(
                    {
                        "music-job-1": {
                            "outputs": {
                                "9": {
                                    "audio": [
                                        {"filename": "song.mp3", "subfolder": "", "type": "output"},
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
                content=b"music-bytes",
                headers={"content-type": "audio/mpeg"},
            )
        ),
    ]

    provider = build_comfy_music_generation_provider()
    result = await provider["generateMusic"](
        {
            "provider": "comfy",
            "model": "workflow",
            "prompt": "gentle ambient synth loop",
            "cfg": {
                "plugins": {
                    "entries": {
                        "comfy": {
                            "config": {
                                "music": {
                                    "workflow": {
                                        "6": {"inputs": {"text": ""}},
                                        "9": {"inputs": {}},
                                    },
                                    "promptNodeId": "6",
                                    "outputNodeId": "9",
                                },
                            },
                        },
                    },
                },
            },
        }
    )

    assert result == {
        "model": "workflow",
        "tracks": [
            {
                "buffer": b"music-bytes",
                "mimeType": "audio/mpeg",
                "fileName": "song.mp3",
            }
        ],
        "metadata": {
            "promptId": "music-job-1",
            "outputNodeIds": ["9"],
            "inputImageCount": 0,
        },
    }


@pytest.mark.asyncio
async def test_rejects_generated_music_downloads_that_exceed_media_cap(
    fetch_guard_mock: AsyncMock,
) -> None:
    set_comfy_fetch_guard_for_testing(fetch_guard_mock)
    fetch_guard_mock.side_effect = [
        _fetch_guard_result(
            _MockResponse(
                content=json.dumps({"prompt_id": "music-job-1"}).encode("utf-8"),
                headers={"content-type": "application/json"},
            )
        ),
        _fetch_guard_result(
            _MockResponse(
                content=json.dumps(
                    {
                        "music-job-1": {
                            "outputs": {
                                "9": {
                                    "audio": [
                                        {"filename": "song.mp3", "subfolder": "", "type": "output"},
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
                headers={"content-type": "audio/mpeg"},
            )
        ),
    ]

    provider = build_comfy_music_generation_provider()
    with pytest.raises(RuntimeError, match="Comfy music output download exceeds 1 bytes"):
        await provider["generateMusic"](
            {
                "provider": "comfy",
                "model": "workflow",
                "prompt": "gentle ambient synth loop",
                "cfg": {
                    "plugins": {
                        "entries": {
                            "comfy": {
                                "config": {
                                    "music": {
                                        "workflow": {
                                            "6": {"inputs": {"text": ""}},
                                            "9": {"inputs": {}},
                                        },
                                        "promptNodeId": "6",
                                        "outputNodeId": "9",
                                    },
                                },
                            },
                        },
                    },
                    "agents": {"defaults": {"mediaMaxMb": 0.000001}},
                },
            }
        )
