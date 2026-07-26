"""Tests for the Comfy image generation provider."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock

import pytest

from openclaw.packages.normalization_core import MAX_TIMER_TIMEOUT_MS
from openclaw_extensions.comfy.image_generation_provider import (
    build_comfy_image_generation_provider,
)
from openclaw_extensions.comfy.test_helpers import (
    build_comfy_config,
    build_legacy_comfy_config,
    mock_comfy_cloud_job_responses,
    mock_comfy_provider_api_key,
    parse_comfy_json_body,
)
from openclaw_extensions.comfy.workflow_runtime import set_comfy_fetch_guard_for_testing


class _MockResponse:
    def __init__(
        self,
        *,
        content: bytes,
        status: int = 200,
        headers: dict[str, str] | None = None,
        ok: bool | None = None,
    ) -> None:
        self._content = content
        self.status = status
        self.ok = ok if ok is not None else 200 <= status < 300
        self.headers = headers or {}

    async def json(self) -> Any:
        return json.loads(self._content.decode("utf-8"))

    async def aread(self) -> bytes:
        return self._content


def _fetch_guard_result(response: _MockResponse) -> dict[str, Any]:
    return {"response": response, "release": AsyncMock()}


def _fetch_request(fetch_guard_mock: AsyncMock, call: int) -> dict[str, Any]:
    return fetch_guard_mock.call_args_list[call - 1].args[0]


def _parse_json_body(fetch_guard_mock: AsyncMock, call: int) -> dict[str, Any]:
    return parse_comfy_json_body(fetch_guard_mock, call)


@pytest.fixture
def fetch_guard_mock() -> AsyncMock:
    return AsyncMock()


@pytest.fixture(autouse=True)
def _reset_fetch_guard() -> Any:
    yield
    set_comfy_fetch_guard_for_testing(None)


@pytest.mark.asyncio
async def test_treats_local_comfy_workflows_as_configured_without_api_key() -> None:
    provider = build_comfy_image_generation_provider()
    assert provider["isConfigured"](
        {
            "cfg": build_comfy_config(
                {
                    "workflow": {"6": {"inputs": {"text": ""}}},
                    "promptNodeId": "6",
                }
            ),
        }
    )


@pytest.mark.asyncio
async def test_falls_back_to_legacy_models_providers_comfy_config() -> None:
    provider = build_comfy_image_generation_provider()
    assert provider["isConfigured"](
        {
            "cfg": build_legacy_comfy_config(
                {
                    "workflow": {"6": {"inputs": {"text": ""}}},
                    "promptNodeId": "6",
                }
            ),
        }
    )


@pytest.mark.asyncio
async def test_treats_cloud_comfy_workflows_as_configured_with_plugin_api_key() -> None:
    provider = build_comfy_image_generation_provider()
    assert provider["isConfigured"](
        {
            "cfg": build_comfy_config(
                {
                    "mode": "cloud",
                    "apiKey": "comfy-test-key",
                    "image": {
                        "workflow": {"6": {"inputs": {"text": ""}}},
                        "promptNodeId": "6",
                    },
                }
            ),
        }
    )


@pytest.mark.asyncio
async def test_treats_cloud_comfy_workflows_as_configured_with_env_secret_ref(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMFY_TEST_API_KEY", "comfy-secret-ref-key")
    provider = build_comfy_image_generation_provider()
    assert provider["isConfigured"](
        {
            "cfg": build_comfy_config(
                {
                    "mode": "cloud",
                    "apiKey": {
                        "source": "env",
                        "provider": "default",
                        "id": "COMFY_TEST_API_KEY",
                    },
                    "image": {
                        "workflow": {"6": {"inputs": {"text": ""}}},
                        "promptNodeId": "6",
                    },
                }
            ),
        }
    )


@pytest.mark.asyncio
async def test_submits_local_workflow_waits_for_history_and_downloads_images(
    fetch_guard_mock: AsyncMock,
) -> None:
    set_comfy_fetch_guard_for_testing(fetch_guard_mock)
    fetch_guard_mock.side_effect = [
        _fetch_guard_result(
            _MockResponse(
                content=json.dumps({"prompt_id": "local-prompt-1"}).encode("utf-8"),
                headers={"content-type": "application/json"},
            )
        ),
        _fetch_guard_result(
            _MockResponse(
                content=json.dumps(
                    {
                        "local-prompt-1": {
                            "outputs": {
                                "9": {
                                    "images": [
                                        {
                                            "filename": "generated.png",
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
                content=b"png-data",
                headers={"content-type": "image/png"},
            )
        ),
    ]

    provider = build_comfy_image_generation_provider()
    result = await provider["generateImage"](
        {
            "provider": "comfy",
            "model": "workflow",
            "prompt": "draw a lobster",
            "cfg": build_comfy_config(
                {
                    "workflow": {
                        "6": {"inputs": {"text": ""}},
                        "9": {"inputs": {}},
                    },
                    "promptNodeId": "6",
                    "outputNodeId": "9",
                }
            ),
        }
    )

    submit_request = _fetch_request(fetch_guard_mock, 1)
    assert submit_request["url"] == "http://127.0.0.1:8188/prompt"
    assert submit_request["auditContext"] == "comfy-image-generate"
    assert _parse_json_body(fetch_guard_mock, 1) == {
        "prompt": {
            "6": {"inputs": {"text": "draw a lobster"}},
            "9": {"inputs": {}},
        },
    }
    history_request = _fetch_request(fetch_guard_mock, 2)
    assert history_request["url"] == "http://127.0.0.1:8188/history/local-prompt-1"
    assert history_request["auditContext"] == "comfy-history"
    download_request = _fetch_request(fetch_guard_mock, 3)
    assert download_request["url"] == (
        "http://127.0.0.1:8188/view?filename=generated.png&subfolder=&type=output"
    )
    assert download_request["auditContext"] == "comfy-image-download"
    assert result == {
        "images": [
            {
                "buffer": b"png-data",
                "mimeType": "image/png",
                "fileName": "generated.png",
                "metadata": {
                    "nodeId": "9",
                    "promptId": "local-prompt-1",
                },
            }
        ],
        "model": "workflow",
        "metadata": {
            "promptId": "local-prompt-1",
            "outputNodeIds": ["9"],
        },
    }


@pytest.mark.asyncio
async def test_caps_oversized_local_workflow_timeouts(
    fetch_guard_mock: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    set_comfy_fetch_guard_for_testing(fetch_guard_mock)
    times = iter([0, 0, MAX_TIMER_TIMEOUT_MS + 1])
    monkeypatch.setattr(
        "openclaw_extensions.comfy.workflow_runtime.time.time",
        lambda: next(times) / 1000,
    )
    fetch_guard_mock.side_effect = [
        _fetch_guard_result(
            _MockResponse(
                content=json.dumps({"prompt_id": "local-prompt-1"}).encode("utf-8"),
                headers={"content-type": "application/json"},
            )
        ),
        _fetch_guard_result(
            _MockResponse(
                content=json.dumps({"local-prompt-1": {"outputs": {}}}).encode("utf-8"),
                headers={"content-type": "application/json"},
            )
        ),
    ]

    provider = build_comfy_image_generation_provider()
    with pytest.raises(RuntimeError, match="Comfy workflow did not finish within 2147000s"):
        await provider["generateImage"](
            {
                "provider": "comfy",
                "model": "workflow",
                "prompt": "draw a bounded timer",
                "cfg": build_comfy_config(
                    {
                        "workflow": {
                            "6": {"inputs": {"text": ""}},
                            "9": {"inputs": {}},
                        },
                        "promptNodeId": "6",
                        "outputNodeId": "9",
                        "timeoutMs": 9_007_199_254_740_991,
                    }
                ),
            }
        )

    assert _fetch_request(fetch_guard_mock, 1)["timeoutMs"] == MAX_TIMER_TIMEOUT_MS
    assert _fetch_request(fetch_guard_mock, 2)["timeoutMs"] == MAX_TIMER_TIMEOUT_MS


@pytest.mark.asyncio
async def test_rejects_generated_image_downloads_that_exceed_media_cap(
    fetch_guard_mock: AsyncMock,
) -> None:
    set_comfy_fetch_guard_for_testing(fetch_guard_mock)
    fetch_guard_mock.side_effect = [
        _fetch_guard_result(
            _MockResponse(
                content=json.dumps({"prompt_id": "local-prompt-1"}).encode("utf-8"),
                headers={"content-type": "application/json"},
            )
        ),
        _fetch_guard_result(
            _MockResponse(
                content=json.dumps(
                    {
                        "local-prompt-1": {
                            "outputs": {
                                "9": {
                                    "images": [
                                        {
                                            "filename": "generated.png",
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
                headers={"content-type": "image/png"},
            )
        ),
    ]

    provider = build_comfy_image_generation_provider()
    cfg = build_comfy_config(
        {
            "workflow": {
                "6": {"inputs": {"text": ""}},
                "9": {"inputs": {}},
            },
            "promptNodeId": "6",
            "outputNodeId": "9",
        }
    )
    cfg["agents"] = {"defaults": {"mediaMaxMb": 0.000001}}
    with pytest.raises(RuntimeError, match="Comfy image output download exceeds 1 bytes"):
        await provider["generateImage"](
            {
                "provider": "comfy",
                "model": "workflow",
                "prompt": "draw a lobster",
                "cfg": cfg,
            }
        )


@pytest.mark.asyncio
async def test_reports_malformed_local_workflow_submit_json(
    fetch_guard_mock: AsyncMock,
) -> None:
    set_comfy_fetch_guard_for_testing(fetch_guard_mock)
    release = AsyncMock()
    fetch_guard_mock.side_effect = [
        {
            "response": _MockResponse(
                content=b"{ nope",
                headers={"content-type": "application/json"},
            ),
            "release": release,
        }
    ]

    provider = build_comfy_image_generation_provider()
    with pytest.raises(RuntimeError, match="Comfy workflow submit failed: malformed JSON response"):
        await provider["generateImage"](
            {
                "provider": "comfy",
                "model": "workflow",
                "prompt": "draw a lobster",
                "cfg": build_comfy_config(
                    {
                        "workflow": {
                            "6": {"inputs": {"text": ""}},
                            "9": {"inputs": {}},
                        },
                        "promptNodeId": "6",
                        "outputNodeId": "9",
                    }
                ),
            }
        )
    release.assert_awaited_once()


@pytest.mark.asyncio
async def test_uploads_reference_images_for_local_edit_workflows(
    fetch_guard_mock: AsyncMock,
) -> None:
    set_comfy_fetch_guard_for_testing(fetch_guard_mock)
    fetch_guard_mock.side_effect = [
        _fetch_guard_result(
            _MockResponse(
                content=json.dumps({"name": "upload.png"}).encode("utf-8"),
                headers={"content-type": "application/json"},
            )
        ),
        _fetch_guard_result(
            _MockResponse(
                content=json.dumps({"prompt_id": "local-edit-1"}).encode("utf-8"),
                headers={"content-type": "application/json"},
            )
        ),
        _fetch_guard_result(
            _MockResponse(
                content=json.dumps(
                    {
                        "local-edit-1": {
                            "outputs": {
                                "9": {
                                    "images": [
                                        {
                                            "filename": "edited.png",
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
                content=b"edited-data",
                headers={"content-type": "image/png"},
            )
        ),
    ]

    provider = build_comfy_image_generation_provider()
    await provider["generateImage"](
        {
            "provider": "comfy",
            "model": "workflow",
            "prompt": "turn this into a poster",
            "cfg": build_comfy_config(
                {
                    "workflow": {
                        "6": {"inputs": {"text": ""}},
                        "7": {"inputs": {"image": ""}},
                        "9": {"inputs": {}},
                    },
                    "promptNodeId": "6",
                    "inputImageNodeId": "7",
                    "outputNodeId": "9",
                }
            ),
            "inputImages": [
                {
                    "buffer": b"source",
                    "mimeType": "image/png",
                    "fileName": "source.png",
                }
            ],
        }
    )

    upload_request = _fetch_request(fetch_guard_mock, 1)
    assert upload_request["url"] == "http://127.0.0.1:8188/upload/image"
    assert upload_request["auditContext"] == "comfy-image-upload"
    assert upload_request["init"]["method"] == "POST"
    upload_form = upload_request["init"]["body"]
    from openclaw_extensions.comfy.workflow_runtime import ComfyMultipartForm

    assert isinstance(upload_form, ComfyMultipartForm)
    assert upload_form.get("type") == "input"
    assert upload_form.get("overwrite") == "true"
    assert _parse_json_body(fetch_guard_mock, 2) == {
        "prompt": {
            "6": {"inputs": {"text": "turn this into a poster"}},
            "7": {"inputs": {"image": "upload.png"}},
            "9": {"inputs": {}},
        },
    }


@pytest.mark.asyncio
async def test_uses_cloud_endpoints_auth_headers_and_partner_node_extra_data(
    fetch_guard_mock: AsyncMock,
) -> None:
    with mock_comfy_provider_api_key():
        set_comfy_fetch_guard_for_testing(fetch_guard_mock)
        mock_comfy_cloud_job_responses(
            fetch_guard_mock,
            body=b"cloud-data",
            content_type="image/png",
            filename="cloud.png",
            output_kind="images",
            prompt_id="cloud-job-1",
            redirect_location="https://cdn.example.com/cloud.png",
        )

        provider = build_comfy_image_generation_provider()
        result = await provider["generateImage"](
            {
                "provider": "comfy",
                "model": "workflow",
                "prompt": "cloud workflow prompt",
                "cfg": build_comfy_config(
                    {
                        "mode": "cloud",
                        "workflow": {
                            "6": {"inputs": {"text": ""}},
                            "9": {"inputs": {}},
                        },
                        "promptNodeId": "6",
                        "outputNodeId": "9",
                    }
                ),
            }
        )

    submit_request = _fetch_request(fetch_guard_mock, 1)
    assert submit_request["url"] == "https://cloud.comfy.org/api/prompt"
    assert submit_request["auditContext"] == "comfy-image-generate"
    submit_headers = submit_request["init"]["headers"]
    assert submit_headers.get("X-API-Key") == "comfy-test-key"
    assert _parse_json_body(fetch_guard_mock, 1) == {
        "prompt": {
            "6": {"inputs": {"text": "cloud workflow prompt"}},
            "9": {"inputs": {}},
        },
        "extra_data": {
            "api_key_comfy_org": "comfy-test-key",
        },
    }
    status_request = _fetch_request(fetch_guard_mock, 2)
    assert status_request["url"] == "https://cloud.comfy.org/api/job/cloud-job-1/status"
    assert status_request["auditContext"] == "comfy-status"
    history_request = _fetch_request(fetch_guard_mock, 3)
    assert history_request["url"] == "https://cloud.comfy.org/api/history_v2/cloud-job-1"
    assert history_request["auditContext"] == "comfy-history"
    view_request = _fetch_request(fetch_guard_mock, 4)
    assert view_request["url"] == (
        "https://cloud.comfy.org/api/view?filename=cloud.png&subfolder=&type=output"
    )
    assert view_request["auditContext"] == "comfy-image-download"
    cdn_request = _fetch_request(fetch_guard_mock, 5)
    assert cdn_request["url"] == "https://cdn.example.com/cloud.png"
    assert cdn_request["auditContext"] == "comfy-image-download"
    assert result["metadata"] == {
        "promptId": "cloud-job-1",
        "outputNodeIds": ["9"],
    }


@pytest.mark.asyncio
async def test_uses_plugin_config_env_secret_ref_auth_for_cloud_workflows(
    fetch_guard_mock: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMFY_TEST_API_KEY", "comfy-secret-ref-key")
    set_comfy_fetch_guard_for_testing(fetch_guard_mock)
    mock_comfy_cloud_job_responses(
        fetch_guard_mock,
        body=b"cloud-data",
        content_type="image/png",
        filename="cloud.png",
        output_kind="images",
        prompt_id="cloud-secret-ref-1",
        redirect_location="https://cdn.example.com/cloud.png",
    )

    provider = build_comfy_image_generation_provider()
    await provider["generateImage"](
        {
            "provider": "comfy",
            "model": "workflow",
            "prompt": "cloud workflow prompt",
            "cfg": build_comfy_config(
                {
                    "mode": "cloud",
                    "apiKey": {
                        "source": "env",
                        "provider": "default",
                        "id": "COMFY_TEST_API_KEY",
                    },
                    "workflow": {
                        "6": {"inputs": {"text": ""}},
                        "9": {"inputs": {}},
                    },
                    "promptNodeId": "6",
                    "outputNodeId": "9",
                }
            ),
        }
    )

    submit_request = _fetch_request(fetch_guard_mock, 1)
    submit_headers = submit_request["init"]["headers"]
    assert submit_headers.get("X-API-Key") == "comfy-secret-ref-key"
    request_body = _parse_json_body(fetch_guard_mock, 1)
    assert request_body["extra_data"]["api_key_comfy_org"] == "comfy-secret-ref-key"


@pytest.mark.asyncio
async def test_uses_provider_auth_fallback_for_cloud_workflows_without_plugin_api_keys(
    fetch_guard_mock: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMFY_API_KEY", "stale-env-key")
    with mock_comfy_provider_api_key("profile-key"):
        set_comfy_fetch_guard_for_testing(fetch_guard_mock)
        mock_comfy_cloud_job_responses(
            fetch_guard_mock,
            body=b"cloud-data",
            content_type="image/png",
            filename="cloud.png",
            output_kind="images",
            prompt_id="cloud-profile-1",
            redirect_location="https://cdn.example.com/cloud.png",
        )

        provider = build_comfy_image_generation_provider()
        await provider["generateImage"](
            {
                "provider": "comfy",
                "model": "workflow",
                "prompt": "cloud workflow prompt",
                "cfg": build_comfy_config(
                    {
                        "mode": "cloud",
                        "workflow": {
                            "6": {"inputs": {"text": ""}},
                            "9": {"inputs": {}},
                        },
                        "promptNodeId": "6",
                        "outputNodeId": "9",
                    }
                ),
            }
        )

    submit_request = _fetch_request(fetch_guard_mock, 1)
    submit_headers = submit_request["init"]["headers"]
    assert submit_headers.get("X-API-Key") == "profile-key"
    request_body = _parse_json_body(fetch_guard_mock, 1)
    assert request_body["extra_data"]["api_key_comfy_org"] == "profile-key"
