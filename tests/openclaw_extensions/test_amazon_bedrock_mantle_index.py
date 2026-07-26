"""Tests for Amazon Bedrock Mantle plugin registration."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from openclaw.plugin_sdk.plugin_test_runtime import create_captured_plugin_registration
from openclaw_extensions.amazon_bedrock_mantle.index import default as bedrock_mantle_plugin


def _register_provider() -> dict[str, Any]:
    captured = create_captured_plugin_registration(id="amazon-bedrock-mantle")
    bedrock_mantle_plugin.register(captured.api)
    assert captured.providers, "expected Amazon Bedrock Mantle provider"
    provider = captured.providers[0]
    assert provider["id"] == "amazon-bedrock-mantle"
    return provider


@pytest.mark.asyncio
async def test_uses_live_plugin_config_to_disable_catalog_discovery() -> None:
    discover_mock = AsyncMock(side_effect=RuntimeError("unexpected fetch"))
    provider = _register_provider()
    catalog = provider.get("catalog")
    assert catalog is not None

    with patch(
        "openclaw_extensions.amazon_bedrock_mantle.discovery.discover_mantle_models",
        discover_mock,
    ):
        result = await catalog["run"](
            {
                "config": {
                    "plugins": {
                        "entries": {
                            "amazon-bedrock-mantle": {
                                "config": {
                                    "discovery": {"enabled": False},
                                },
                            },
                        },
                    },
                },
                "env": {
                    "AWS_BEARER_TOKEN_BEDROCK": "test-token",
                    "AWS_REGION": "us-east-1",
                },
            }
        )

    assert result is None
    discover_mock.assert_not_awaited()


def test_registers_with_correct_provider_id_and_label() -> None:
    provider = _register_provider()
    assert provider["id"] == "amazon-bedrock-mantle"
    assert provider["label"] == "Amazon Bedrock Mantle (OpenAI-compatible)"


def test_classifies_rate_limit_errors_for_failover() -> None:
    provider = _register_provider()
    classify = provider.get("classifyFailoverReason")
    assert callable(classify)
    assert classify({"errorMessage": "rate_limit exceeded"}) == "rate_limit"
    assert classify({"errorMessage": "429 Too Many Requests"}) == "rate_limit"
    assert classify({"errorMessage": "some other error"}) is None
    assert classify({"errorMessage": "overloaded_error"}) == "overloaded"


def test_provides_custom_stream_only_for_mantle_anthropic_models() -> None:
    provider = _register_provider()
    create_stream_fn = provider.get("createStreamFn")
    assert callable(create_stream_fn)
    assert callable(
        create_stream_fn(
            {
                "provider": "amazon-bedrock-mantle",
                "modelId": "anthropic.claude-opus-4-7",
                "model": {"api": "anthropic-messages"},
            }
        )
    )
    assert (
        create_stream_fn(
            {
                "provider": "amazon-bedrock-mantle",
                "modelId": "openai.gpt-oss-120b",
                "model": {"api": "openai-completions"},
            }
        )
        is None
    )
