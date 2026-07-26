"""Tests for Chutes model catalog and discovery."""

from __future__ import annotations

import json
import os
from collections.abc import Awaitable, Callable
from contextlib import contextmanager
from typing import Any
from unittest.mock import AsyncMock

import pytest

import openclaw_extensions.chutes.models as chutes_models
from openclaw_extensions.chutes.api import (
    CHUTES_MODEL_CATALOG,
    build_chutes_model_definition,
    clear_chutes_model_cache_for_tests,
    discover_chutes_models,
)


def _restore_env_var(name: str, value: str | None) -> None:
    if value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = value


class _MockFetchResponse:
    def __init__(self, payload: Any = None, *, status: int = 200, raw_body: bytes = b"") -> None:
        self.ok = 200 <= status < 300
        self.status = status
        self.bodyUsed = False
        if payload is not None:
            self._data = json.dumps(payload).encode("utf-8")
        else:
            self._data = raw_body

    async def aread(self) -> bytes:
        return self._data

    async def json(self) -> Any:
        return json.loads(self._data)


def _read_authorization_header(init: dict[str, Any] | None) -> str:
    headers = (init or {}).get("headers") or {}
    if isinstance(headers, dict):
        return headers.get("Authorization") or headers.get("authorization") or ""
    return ""


@contextmanager
def _with_live_chutes_discovery(
    fetch_mock: Callable[..., Awaitable[dict[str, Any]]],
    *,
    now_ms: list[int] | None = None,
):
    old_node_env = os.environ.get("NODE_ENV")
    old_vitest = os.environ.get("VITEST")
    os.environ.pop("NODE_ENV", None)
    os.environ.pop("VITEST", None)
    previous_now = chutes_models._discovery_now
    if now_ms is not None:
        chutes_models._discovery_now = lambda: now_ms[0]

    async def fetch_guard(params: dict[str, Any]) -> dict[str, Any]:
        response = await fetch_mock(params["url"], params.get("init"))

        async def release() -> None:
            return None

        return {"response": response, "release": release}

    import openclaw.plugin_sdk.provider_catalog_live_runtime as live_runtime

    previous_guard = live_runtime._default_fetch_guard
    live_runtime._default_fetch_guard = fetch_guard
    try:
        yield
    finally:
        live_runtime._default_fetch_guard = previous_guard
        chutes_models._discovery_now = previous_now
        _restore_env_var("NODE_ENV", old_node_env)
        _restore_env_var("VITEST", old_vitest)


def _create_auth_echo_fetch_mock() -> AsyncMock:
    async def fetch_mock(_url: str, init: dict[str, Any] | None = None) -> _MockFetchResponse:
        auth = _read_authorization_header(init)
        model_id = f"{auth.removeprefix('Bearer ').strip()}-model" if auth else "public-model"
        return _MockFetchResponse({"data": [{"id": model_id}]})

    return AsyncMock(side_effect=fetch_mock)


@pytest.fixture(autouse=True)
def _clear_chutes_cache() -> None:
    clear_chutes_model_cache_for_tests()
    yield
    clear_chutes_model_cache_for_tests()


def test_build_chutes_model_definition_returns_config_with_required_fields() -> None:
    entry = CHUTES_MODEL_CATALOG[0]
    definition = build_chutes_model_definition(entry)
    assert definition["id"] == entry["id"]
    assert definition["name"] == entry["name"]
    assert definition["reasoning"] == entry["reasoning"]
    assert definition["input"] == entry["input"]
    assert definition["cost"] == entry["cost"]
    assert definition["contextWindow"] == entry["contextWindow"]
    assert definition["maxTokens"] == entry["maxTokens"]
    assert definition["compat"]["supportsUsageInStreaming"] is False


def test_keeps_qwen_vl_image_limits_in_the_runtime_catalog() -> None:
    vision_model_ids = [
        "Qwen/Qwen2.5-VL-32B-Instruct",
        "Qwen/Qwen3-VL-235B-A22B-Instruct",
    ]
    for model_id in vision_model_ids:
        model = next(
            (candidate for candidate in CHUTES_MODEL_CATALOG if candidate["id"] == model_id), None
        )
        assert model is not None
        assert build_chutes_model_definition(model)["mediaInput"] == {
            "image": {
                "maxPixels": 12845056,
                "preferredSidePx": 2048,
                "tokenMode": "provider",
            }
        }


@pytest.mark.asyncio
async def test_discover_chutes_models_returns_static_catalog_when_access_token_empty() -> None:
    models = await discover_chutes_models("")
    assert len(models) == len(CHUTES_MODEL_CATALOG)
    assert [model["id"] for model in models] == [model["id"] for model in CHUTES_MODEL_CATALOG]


@pytest.mark.asyncio
async def test_discover_chutes_models_returns_static_catalog_in_test_env_by_default() -> None:
    models = await discover_chutes_models("test-token")
    assert len(models) == len(CHUTES_MODEL_CATALOG)
    assert models[0]["id"] == "Qwen/Qwen3-32B"


@pytest.mark.asyncio
async def test_discover_chutes_models_correctly_maps_api_response_when_not_in_test_env() -> None:
    async def fetch_mock(_url: str, _init: dict[str, Any] | None = None) -> _MockFetchResponse:
        return _MockFetchResponse(
            {
                "data": [
                    {"id": "zai-org/GLM-4.7-TEE"},
                    {
                        "id": "new-provider/new-model-r1",
                        "supported_features": ["reasoning"],
                        "input_modalities": ["text", "image"],
                        "context_length": 200000,
                        "max_output_length": 16384,
                        "pricing": {"prompt": 0.1, "completion": 0.2},
                    },
                    {"id": "new-provider/simple-model"},
                ]
            }
        )

    with _with_live_chutes_discovery(fetch_mock):
        models = await discover_chutes_models("test-token-real-fetch")
        assert len(models) > 0
        if len(models) == 3:
            assert models[0]["id"] == "zai-org/GLM-4.7-TEE"
            assert models[1]["reasoning"] is True
            assert models[1]["compat"]["supportsUsageInStreaming"] is False


@pytest.mark.asyncio
async def test_falls_back_from_malformed_live_token_metadata() -> None:
    async def fetch_mock(_url: str, _init: dict[str, Any] | None = None) -> _MockFetchResponse:
        return _MockFetchResponse(
            {
                "data": [
                    {
                        "id": "provider/bad-window",
                        "context_length": -1,
                        "max_output_length": 16384.5,
                    },
                    {
                        "id": "provider/bad-max-output",
                        "context_length": float("inf"),
                        "max_output_length": 0,
                    },
                ]
            }
        )

    with _with_live_chutes_discovery(fetch_mock):
        models = await discover_chutes_models("malformed-token-metadata")
        assert models[0] == {
            "id": "provider/bad-window",
            "name": "provider/bad-window",
            "reasoning": False,
            "input": ["text"],
            "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
            "contextWindow": 128000,
            "maxTokens": 4096,
            "compat": {"supportsUsageInStreaming": False},
        }
        assert models[1]["id"] == "provider/bad-max-output"
        assert models[1]["contextWindow"] == 128000
        assert models[1]["maxTokens"] == 4096


@pytest.mark.asyncio
async def test_discover_chutes_models_retries_without_auth_on_401() -> None:
    async def fetch_mock(_url: str, init: dict[str, Any] | None = None) -> _MockFetchResponse:
        if _read_authorization_header(init) == "Bearer test-token-error":
            return _MockFetchResponse(status=401)
        return _MockFetchResponse(
            {
                "data": [
                    {
                        "id": "Qwen/Qwen3-32B",
                        "name": "Qwen/Qwen3-32B",
                        "supported_features": ["reasoning"],
                        "input_modalities": ["text"],
                        "context_length": 40960,
                        "max_output_length": 40960,
                        "pricing": {"prompt": 0.08, "completion": 0.24},
                    },
                    {
                        "id": "unsloth/Mistral-Nemo-Instruct-2407",
                        "name": "unsloth/Mistral-Nemo-Instruct-2407",
                        "input_modalities": ["text"],
                        "context_length": 131072,
                        "max_output_length": 131072,
                        "pricing": {"prompt": 0.02, "completion": 0.04},
                    },
                    {
                        "id": "deepseek-ai/DeepSeek-V3-0324-TEE",
                        "name": "deepseek-ai/DeepSeek-V3-0324-TEE",
                        "supported_features": ["reasoning"],
                        "input_modalities": ["text"],
                        "context_length": 131072,
                        "max_output_length": 65536,
                        "pricing": {"prompt": 0.28, "completion": 0.42},
                    },
                ]
            }
        )

    fetch_mock_obj = AsyncMock(side_effect=fetch_mock)
    with _with_live_chutes_discovery(fetch_mock_obj):
        models = await discover_chutes_models("test-token-error")
        assert len(models) > 0
        assert fetch_mock_obj.await_count > 0


@pytest.mark.asyncio
async def test_does_not_cache_fallback_static_catalog_for_non_ok_responses() -> None:
    fetch_mock = AsyncMock(return_value=_MockFetchResponse(status=503))
    with _with_live_chutes_discovery(fetch_mock):
        first = await discover_chutes_models("chutes-fallback-token")
        second = await discover_chutes_models("chutes-fallback-token")
        assert [model["id"] for model in first] == [model["id"] for model in CHUTES_MODEL_CATALOG]
        assert [model["id"] for model in second] == [model["id"] for model in CHUTES_MODEL_CATALOG]
        assert fetch_mock.await_count == 2


@pytest.mark.asyncio
async def test_scopes_discovery_cache_by_access_token() -> None:
    fetch_mock = _create_auth_echo_fetch_mock()
    with _with_live_chutes_discovery(fetch_mock):
        models_a = await discover_chutes_models("chutes-token-a")
        models_b = await discover_chutes_models("chutes-token-b")
        models_a_second = await discover_chutes_models("chutes-token-a")
        assert models_a[0]["id"] == "chutes-token-a-model"
        assert models_b[0]["id"] == "chutes-token-b-model"
        assert models_a_second[0]["id"] == "chutes-token-a-model"
        assert fetch_mock.await_count == 2


@pytest.mark.asyncio
async def test_evicts_oldest_token_entries_when_cache_reaches_max_size() -> None:
    fetch_mock = _create_auth_echo_fetch_mock()
    with _with_live_chutes_discovery(fetch_mock):
        for index in range(150):
            await discover_chutes_models(f"cache-token-{index}")
        await discover_chutes_models("cache-token-0")
        assert fetch_mock.await_count == 151


@pytest.mark.asyncio
async def test_prunes_expired_token_cache_entries_during_subsequent_discovery() -> None:
    now_ms = [1_772_313_600_000]
    fetch_mock = _create_auth_echo_fetch_mock()
    with _with_live_chutes_discovery(fetch_mock, now_ms=now_ms):
        await discover_chutes_models("token-a")
        now_ms[0] += 5 * 60 * 1000 + 1
        await discover_chutes_models("token-b")
        await discover_chutes_models("token-a")
        assert fetch_mock.await_count == 3


@pytest.mark.asyncio
async def test_does_not_cache_401_fallback_under_the_failed_token_key() -> None:
    async def fetch_mock(_url: str, init: dict[str, Any] | None = None) -> _MockFetchResponse:
        if _read_authorization_header(init) == "Bearer failed-token":
            return _MockFetchResponse(status=401)
        return _MockFetchResponse({"data": [{"id": "public/model"}]})

    fetch_mock_obj = AsyncMock(side_effect=fetch_mock)
    with _with_live_chutes_discovery(fetch_mock_obj):
        await discover_chutes_models("failed-token")
        await discover_chutes_models("failed-token")
        assert fetch_mock_obj.await_count == 3
