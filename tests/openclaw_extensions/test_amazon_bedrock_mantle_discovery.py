"""Tests for Amazon Bedrock Mantle discovery and bearer-token helpers."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from openclaw_extensions.amazon_bedrock_mantle.api import (
    MANTLE_IAM_TOKEN_MARKER,
    discover_mantle_models,
    generate_bearer_token_from_iam,
    get_cached_iam_token,
    merge_implicit_mantle_provider,
    reset_iam_token_cache_for_test,
    reset_mantle_discovery_cache_for_test,
    resolve_implicit_mantle_provider,
    resolve_mantle_bearer_token,
    resolve_mantle_runtime_bearer_token,
)


def _create_token_provider_factory(token_provider: AsyncMock) -> MagicMock:
    return MagicMock(return_value=token_provider)


def _arg_at(mock: AsyncMock, call_index: int, arg_index: int) -> Any:
    call = mock.call_args_list[call_index]
    return call.args[arg_index]


def _object_arg_at(mock: AsyncMock, call_index: int, arg_index: int) -> dict[str, Any]:
    value = _arg_at(mock, call_index, arg_index)
    assert isinstance(value, dict)
    return value


def _string_arg_at(mock: AsyncMock, call_index: int, arg_index: int) -> str:
    value = _arg_at(mock, call_index, arg_index)
    assert isinstance(value, str)
    return value


@pytest.fixture(autouse=True)
def _reset_caches() -> None:
    reset_mantle_discovery_cache_for_test()
    reset_iam_token_cache_for_test()
    yield
    reset_mantle_discovery_cache_for_test()
    reset_iam_token_cache_for_test()


def test_resolve_mantle_bearer_token_from_env() -> None:
    assert (
        resolve_mantle_bearer_token({"AWS_BEARER_TOKEN_BEDROCK": "bedrock-api-key-abc123"})
        == "bedrock-api-key-abc123"
    )


def test_resolve_mantle_bearer_token_returns_none_when_unset() -> None:
    assert resolve_mantle_bearer_token({}) is None


def test_resolve_mantle_bearer_token_trims_whitespace() -> None:
    assert resolve_mantle_bearer_token({"AWS_BEARER_TOKEN_BEDROCK": "  my-token  "}) == "my-token"


@pytest.mark.asyncio
async def test_generate_bearer_token_from_iam_success() -> None:
    token_provider = AsyncMock(return_value="bedrock-api-key-generated")
    token_provider_factory = _create_token_provider_factory(token_provider)

    token = await generate_bearer_token_from_iam(
        {
            "region": "us-east-1",
            "tokenProviderFactory": token_provider_factory,
        }
    )

    assert token == "bedrock-api-key-generated"
    token_provider_factory.assert_called_once_with(
        {
            "region": "us-east-1",
            "expiresInSeconds": 7200,
        }
    )
    token_provider.assert_awaited_once()


@pytest.mark.asyncio
async def test_generate_bearer_token_from_iam_caches_within_ttl() -> None:
    token_provider = AsyncMock(return_value="bedrock-api-key-cached")
    token_provider_factory = _create_token_provider_factory(token_provider)
    now = 1000

    first = await generate_bearer_token_from_iam(
        {
            "region": "us-east-1",
            "now": lambda: now,
            "tokenProviderFactory": token_provider_factory,
        }
    )
    now += 1800_000
    second = await generate_bearer_token_from_iam(
        {
            "region": "us-east-1",
            "now": lambda: now,
            "tokenProviderFactory": token_provider_factory,
        }
    )

    assert first == second
    token_provider.assert_awaited_once()


@pytest.mark.asyncio
async def test_generate_bearer_token_from_iam_does_not_reuse_across_regions() -> None:
    token_provider = AsyncMock(side_effect=["bedrock-api-key-east", "bedrock-api-key-west"])
    token_provider_factory = _create_token_provider_factory(token_provider)

    east = await generate_bearer_token_from_iam(
        {
            "region": "us-east-1",
            "now": lambda: 1000,
            "tokenProviderFactory": token_provider_factory,
        }
    )
    west = await generate_bearer_token_from_iam(
        {
            "region": "us-west-2",
            "now": lambda: 2000,
            "tokenProviderFactory": token_provider_factory,
        }
    )

    assert east == "bedrock-api-key-east"
    assert west == "bedrock-api-key-west"
    assert token_provider_factory.call_count == 2
    assert token_provider_factory.call_args_list[0].args == (
        {"region": "us-east-1", "expiresInSeconds": 7200},
    )
    assert token_provider_factory.call_args_list[1].args == (
        {"region": "us-west-2", "expiresInSeconds": 7200},
    )
    assert token_provider.await_count == 2


@pytest.mark.asyncio
async def test_generate_bearer_token_from_iam_returns_none_on_failure() -> None:
    def failing_factory(_opts: dict[str, Any] | None = None) -> AsyncMock:
        raise RuntimeError("no credentials")

    assert (
        await generate_bearer_token_from_iam(
            {
                "region": "us-east-1",
                "tokenProviderFactory": failing_factory,
            }
        )
        is None
    )


@pytest.mark.asyncio
async def test_resolve_implicit_mantle_provider_skips_iam_when_discovery_disabled() -> None:
    def failing_factory(_opts: dict[str, Any] | None = None) -> AsyncMock:
        raise RuntimeError("disabled discovery should not generate a token")

    result = await resolve_implicit_mantle_provider(
        {
            "env": {"AWS_REGION": "us-east-1"},
            "pluginConfig": {"discovery": {"enabled": False}},
            "tokenProviderFactory": failing_factory,
        }
    )

    assert result is None


@pytest.mark.asyncio
async def test_get_cached_iam_token_returns_cached_value() -> None:
    token_provider = AsyncMock(return_value="bedrock-cached-token")
    token_provider_factory = _create_token_provider_factory(token_provider)

    await generate_bearer_token_from_iam(
        {
            "region": "us-east-1",
            "tokenProviderFactory": token_provider_factory,
        }
    )

    assert get_cached_iam_token("us-east-1") == "bedrock-cached-token"


def test_get_cached_iam_token_returns_none_when_empty() -> None:
    assert get_cached_iam_token("us-east-1") is None


@pytest.mark.asyncio
async def test_get_cached_iam_token_returns_none_when_expired() -> None:
    token_provider = AsyncMock(return_value="bedrock-expired-token")
    token_provider_factory = _create_token_provider_factory(token_provider)

    await generate_bearer_token_from_iam(
        {
            "region": "us-east-1",
            "now": lambda: 1000,
            "tokenProviderFactory": token_provider_factory,
        }
    )

    assert get_cached_iam_token("us-east-1") is None


@pytest.mark.asyncio
async def test_generate_bearer_token_from_iam_skips_cache_on_ttl_overflow() -> None:
    token_provider = AsyncMock(side_effect=["bedrock-overflow-token-1", "bedrock-overflow-token-2"])
    token_provider_factory = _create_token_provider_factory(token_provider)

    assert (
        await generate_bearer_token_from_iam(
            {
                "region": "us-east-1",
                "now": lambda: 8_640_000_000_000_000,
                "tokenProviderFactory": token_provider_factory,
            }
        )
        == "bedrock-overflow-token-1"
    )
    assert get_cached_iam_token("us-east-1") is None

    assert (
        await generate_bearer_token_from_iam(
            {
                "region": "us-east-1",
                "now": lambda: 8_640_000_000_000_000,
                "tokenProviderFactory": token_provider_factory,
            }
        )
        == "bedrock-overflow-token-2"
    )
    assert token_provider.await_count == 2


@pytest.mark.asyncio
async def test_discover_mantle_models_sorted_by_id() -> None:
    mock_fetch = AsyncMock(
        return_value=_MockFetchResponse(
            ok=True,
            payload={
                "data": [
                    {"id": "openai.gpt-oss-120b", "object": "model", "owned_by": "openai"},
                    {
                        "id": "anthropic.claude-sonnet-4-6",
                        "object": "model",
                        "owned_by": "anthropic",
                    },
                    {"id": "mistral.devstral-2-123b", "object": "model", "owned_by": "mistral"},
                ]
            },
        )
    )

    models = await discover_mantle_models(
        {
            "region": "us-east-1",
            "bearerToken": "test-token",
            "fetchFn": mock_fetch,
        }
    )

    assert len(models) == 3
    assert models[0]["id"] == "anthropic.claude-sonnet-4-6"
    assert models[0]["name"] == "anthropic.claude-sonnet-4-6"
    assert models[0]["reasoning"] is False
    assert models[0]["input"] == ["text"]
    assert models[1]["id"] == "mistral.devstral-2-123b"
    assert models[1]["reasoning"] is False
    assert models[2]["id"] == "openai.gpt-oss-120b"
    assert models[2]["reasoning"] is True
    assert _string_arg_at(mock_fetch, 0, 0) == "https://bedrock-mantle.us-east-1.api.aws/v1/models"
    assert _object_arg_at(mock_fetch, 0, 1)["headers"]["Authorization"] == "Bearer test-token"


@pytest.mark.asyncio
async def test_discover_mantle_models_infers_reasoning_support() -> None:
    mock_fetch = AsyncMock(
        return_value=_MockFetchResponse(
            ok=True,
            payload={
                "data": [
                    {"id": "moonshotai.kimi-k2-thinking", "object": "model"},
                    {"id": "openai.gpt-oss-120b", "object": "model"},
                    {"id": "openai.gpt-oss-safeguard-120b", "object": "model"},
                    {"id": "deepseek.v3.2", "object": "model"},
                    {"id": "mistral.mistral-large-3-675b-instruct", "object": "model"},
                ]
            },
        )
    )

    models = await discover_mantle_models(
        {
            "region": "us-east-1",
            "bearerToken": "test-token",
            "fetchFn": mock_fetch,
        }
    )
    by_id = {model["id"]: model for model in models}
    assert by_id["moonshotai.kimi-k2-thinking"]["reasoning"] is True
    assert by_id["openai.gpt-oss-120b"]["reasoning"] is True
    assert by_id["openai.gpt-oss-safeguard-120b"]["reasoning"] is True
    assert by_id["deepseek.v3.2"]["reasoning"] is False
    assert by_id["mistral.mistral-large-3-675b-instruct"]["reasoning"] is False


@pytest.mark.asyncio
async def test_discover_mantle_models_returns_empty_on_permission_error() -> None:
    mock_fetch = AsyncMock(
        return_value=_MockFetchResponse(ok=False, status=403, status_text="Forbidden")
    )

    models = await discover_mantle_models(
        {
            "region": "us-east-1",
            "bearerToken": "test-token",
            "fetchFn": mock_fetch,
        }
    )

    assert models == []


@pytest.mark.asyncio
async def test_discover_mantle_models_returns_empty_on_network_error() -> None:
    mock_fetch = AsyncMock(side_effect=ConnectionError("ECONNREFUSED"))

    models = await discover_mantle_models(
        {
            "region": "us-east-1",
            "bearerToken": "test-token",
            "fetchFn": mock_fetch,
        }
    )

    assert models == []


@pytest.mark.asyncio
async def test_discover_mantle_models_filters_empty_ids() -> None:
    mock_fetch = AsyncMock(
        return_value=_MockFetchResponse(
            ok=True,
            payload={
                "data": [
                    {"id": "anthropic.claude-sonnet-4-6", "object": "model"},
                    {"id": "", "object": "model"},
                    {"id": "  ", "object": "model"},
                ]
            },
        )
    )

    models = await discover_mantle_models(
        {
            "region": "us-east-1",
            "bearerToken": "test-token",
            "fetchFn": mock_fetch,
        }
    )

    assert len(models) == 1
    assert models[0]["id"] == "anthropic.claude-sonnet-4-6"


@pytest.mark.asyncio
async def test_discover_mantle_models_uses_cache_within_refresh_interval() -> None:
    now = 1_000_000
    mock_fetch = AsyncMock(
        return_value=_MockFetchResponse(
            ok=True,
            payload={"data": [{"id": "anthropic.claude-sonnet-4-6", "object": "model"}]},
        )
    )

    first = await discover_mantle_models(
        {
            "region": "us-east-1",
            "bearerToken": "test-token",
            "fetchFn": mock_fetch,
            "now": lambda: now,
        }
    )
    assert len(first) == 1
    assert mock_fetch.await_count == 1

    now += 60_000
    second = await discover_mantle_models(
        {
            "region": "us-east-1",
            "bearerToken": "test-token",
            "fetchFn": mock_fetch,
            "now": lambda: now,
        }
    )
    assert len(second) == 1
    assert mock_fetch.await_count == 1

    now += 3600_000
    third = await discover_mantle_models(
        {
            "region": "us-east-1",
            "bearerToken": "test-token",
            "fetchFn": mock_fetch,
            "now": lambda: now,
        }
    )
    assert len(third) == 1
    assert mock_fetch.await_count == 2


@pytest.mark.asyncio
async def test_discover_mantle_models_returns_stale_cache_on_fetch_failure() -> None:
    now = 1_000_000
    mock_fetch = AsyncMock(
        side_effect=[
            _MockFetchResponse(
                ok=True,
                payload={"data": [{"id": "anthropic.claude-sonnet-4-6", "object": "model"}]},
            ),
            ConnectionError("ECONNREFUSED"),
        ]
    )

    await discover_mantle_models(
        {
            "region": "us-east-1",
            "bearerToken": "test-token",
            "fetchFn": mock_fetch,
            "now": lambda: now,
        }
    )

    now += 7200_000
    stale = await discover_mantle_models(
        {
            "region": "us-east-1",
            "bearerToken": "test-token",
            "fetchFn": mock_fetch,
            "now": lambda: now,
        }
    )
    assert len(stale) == 1
    assert stale[0]["id"] == "anthropic.claude-sonnet-4-6"


@pytest.mark.asyncio
async def test_resolve_implicit_mantle_provider_with_explicit_token() -> None:
    mock_fetch = AsyncMock(
        return_value=_MockFetchResponse(
            ok=True,
            payload={"data": [{"id": "anthropic.claude-sonnet-4-6", "object": "model"}]},
        )
    )

    provider = await resolve_implicit_mantle_provider(
        {
            "env": {
                "AWS_BEARER_TOKEN_BEDROCK": "my-token",
                "AWS_REGION": "us-east-1",
            },
            "fetchFn": mock_fetch,
        }
    )

    assert provider is not None
    assert provider["baseUrl"] == "https://bedrock-mantle.us-east-1.api.aws/v1"
    assert provider["api"] == "openai-completions"
    assert provider["auth"] == "api-key"
    assert provider["apiKey"] == "env:AWS_BEARER_TOKEN_BEDROCK"
    assert len(provider["models"]) == 3
    opus = next(model for model in provider["models"] if model["id"] == "anthropic.claude-opus-4-7")
    assert opus["api"] == "anthropic-messages"
    assert opus["reasoning"] is False
    assert "baseUrl" not in opus
    mythos = next(
        model for model in provider["models"] if model["id"] == "anthropic.claude-mythos-preview"
    )
    assert mythos == {
        "id": "anthropic.claude-mythos-preview",
        "name": "Claude Mythos Preview",
        "api": "anthropic-messages",
        "reasoning": True,
        "params": {"canonicalModelId": "claude-mythos-preview"},
        "input": ["text", "image"],
        "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
        "contextWindow": 1_000_000,
        "maxTokens": 128_000,
    }


@pytest.mark.asyncio
async def test_resolve_implicit_mantle_provider_returns_none_without_auth() -> None:
    def failing_factory(_opts: dict[str, Any] | None = None) -> AsyncMock:
        raise RuntimeError("no credentials")

    provider = await resolve_implicit_mantle_provider(
        {
            "env": {},
            "tokenProviderFactory": failing_factory,
        }
    )

    assert provider is None


@pytest.mark.asyncio
async def test_resolve_implicit_mantle_provider_uses_generated_iam_token() -> None:
    token_provider = AsyncMock(return_value="bedrock-api-key-iam")
    token_provider_factory = _create_token_provider_factory(token_provider)
    mock_fetch = AsyncMock(
        return_value=_MockFetchResponse(
            ok=True,
            payload={"data": [{"id": "openai.gpt-oss-120b", "object": "model"}]},
        )
    )

    provider = await resolve_implicit_mantle_provider(
        {
            "env": {
                "AWS_PROFILE": "default",
                "AWS_REGION": "us-east-1",
            },
            "fetchFn": mock_fetch,
            "tokenProviderFactory": token_provider_factory,
        }
    )

    assert provider is not None
    assert provider["apiKey"] == MANTLE_IAM_TOKEN_MARKER
    token_provider.assert_awaited_once()
    assert _string_arg_at(mock_fetch, 0, 0) == "https://bedrock-mantle.us-east-1.api.aws/v1/models"
    assert (
        _object_arg_at(mock_fetch, 0, 1)["headers"]["Authorization"] == "Bearer bedrock-api-key-iam"
    )


@pytest.mark.asyncio
async def test_resolve_mantle_runtime_bearer_token_uses_cached_iam_token() -> None:
    token_provider = AsyncMock(return_value="bedrock-api-key-runtime")
    token_provider_factory = _create_token_provider_factory(token_provider)

    await generate_bearer_token_from_iam(
        {
            "region": "us-east-1",
            "now": lambda: 1000,
            "tokenProviderFactory": token_provider_factory,
        }
    )

    resolved = await resolve_mantle_runtime_bearer_token(
        {
            "apiKey": MANTLE_IAM_TOKEN_MARKER,
            "env": {"AWS_REGION": "us-east-1"},
            "now": lambda: 2000,
            "tokenProviderFactory": token_provider_factory,
        }
    )
    assert resolved == {
        "apiKey": "bedrock-api-key-runtime",
        "expiresAt": 1000 + 7200_000,
    }
    token_provider.assert_awaited_once()


@pytest.mark.asyncio
async def test_resolve_mantle_runtime_bearer_token_generates_fresh_token_when_cold() -> None:
    token_provider = AsyncMock(return_value="bedrock-api-key-fresh")
    token_provider_factory = _create_token_provider_factory(token_provider)

    resolved = await resolve_mantle_runtime_bearer_token(
        {
            "apiKey": MANTLE_IAM_TOKEN_MARKER,
            "env": {"AWS_REGION": "us-east-1"},
            "now": lambda: 5000,
            "tokenProviderFactory": token_provider_factory,
        }
    )
    assert resolved == {
        "apiKey": "bedrock-api-key-fresh",
        "expiresAt": 5000 + 7200_000,
    }
    token_provider.assert_awaited_once()


@pytest.mark.asyncio
async def test_resolve_mantle_runtime_bearer_token_omits_expiry_on_invalid_clock() -> None:
    token_provider = AsyncMock(return_value="bedrock-api-key-invalid-clock")
    token_provider_factory = _create_token_provider_factory(token_provider)

    resolved = await resolve_mantle_runtime_bearer_token(
        {
            "apiKey": MANTLE_IAM_TOKEN_MARKER,
            "env": {"AWS_REGION": "us-east-1"},
            "now": lambda: float("nan"),
            "tokenProviderFactory": token_provider_factory,
        }
    )
    assert resolved == {"apiKey": "bedrock-api-key-invalid-clock"}
    token_provider.assert_awaited_once()


@pytest.mark.asyncio
async def test_resolve_implicit_mantle_provider_returns_none_for_unsupported_region() -> None:
    provider = await resolve_implicit_mantle_provider(
        {
            "env": {
                "AWS_BEARER_TOKEN_BEDROCK": "my-token",
                "AWS_REGION": "af-south-1",
            }
        }
    )

    assert provider is None


@pytest.mark.asyncio
async def test_resolve_implicit_mantle_provider_defaults_to_us_east_1() -> None:
    mock_fetch = AsyncMock(
        return_value=_MockFetchResponse(
            ok=True,
            payload={"data": [{"id": "openai.gpt-oss-120b", "object": "model"}]},
        )
    )

    provider = await resolve_implicit_mantle_provider(
        {
            "env": {"AWS_BEARER_TOKEN_BEDROCK": "my-token"},
            "fetchFn": mock_fetch,
        }
    )

    assert provider is not None
    assert provider["baseUrl"] == "https://bedrock-mantle.us-east-1.api.aws/v1"
    assert _string_arg_at(mock_fetch, 0, 0) == "https://bedrock-mantle.us-east-1.api.aws/v1/models"
    _object_arg_at(mock_fetch, 0, 1)


def test_merge_implicit_mantle_provider_uses_implicit_models_when_existing_empty() -> None:
    result = merge_implicit_mantle_provider(
        {
            "existing": {
                "baseUrl": "https://custom.example.com/v1",
                "models": [],
            },
            "implicit": {
                "baseUrl": "https://bedrock-mantle.us-east-1.api.aws/v1",
                "api": "openai-completions",
                "auth": "api-key",
                "apiKey": "env:AWS_BEARER_TOKEN_BEDROCK",
                "models": [
                    {
                        "id": "openai.gpt-oss-120b",
                        "name": "GPT-OSS 120B",
                        "reasoning": True,
                        "input": ["text"],
                        "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
                        "contextWindow": 32000,
                        "maxTokens": 4096,
                    }
                ],
            },
        }
    )

    assert result["baseUrl"] == "https://custom.example.com/v1"
    assert [model["id"] for model in result["models"]] == ["openai.gpt-oss-120b"]


def test_merge_implicit_mantle_provider_preserves_existing_models() -> None:
    result = merge_implicit_mantle_provider(
        {
            "existing": {
                "baseUrl": "https://bedrock-mantle.us-east-1.api.aws/v1",
                "models": [
                    {
                        "id": "custom-model",
                        "name": "My Custom Model",
                        "reasoning": False,
                        "input": ["text"],
                        "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
                        "contextWindow": 64000,
                        "maxTokens": 8192,
                    }
                ],
            },
            "implicit": {
                "baseUrl": "https://bedrock-mantle.us-east-1.api.aws/v1",
                "api": "openai-completions",
                "auth": "api-key",
                "models": [
                    {
                        "id": "openai.gpt-oss-120b",
                        "name": "GPT-OSS 120B",
                        "reasoning": True,
                        "input": ["text"],
                        "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
                        "contextWindow": 32000,
                        "maxTokens": 4096,
                    }
                ],
            },
        }
    )

    assert [model["id"] for model in result["models"]] == ["custom-model"]


class _MockFetchResponse:
    def __init__(
        self,
        *,
        ok: bool,
        payload: dict[str, Any] | None = None,
        status: int = 200,
        status_text: str = "OK",
    ) -> None:
        self.ok = ok
        self.status = status
        self.statusText = status_text
        self._payload = payload or {}

    async def json(self) -> dict[str, Any]:
        return self._payload
