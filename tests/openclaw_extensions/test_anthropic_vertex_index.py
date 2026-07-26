"""Tests for Anthropic Vertex provider plugin registration."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from openclaw.plugin_sdk.plugin_test_runtime import create_captured_plugin_registration
from openclaw_extensions.anthropic_vertex.index import default as anthropic_vertex_plugin


def _register_provider() -> dict[str, Any]:
    captured = create_captured_plugin_registration(id="anthropic-vertex")
    anthropic_vertex_plugin.register(captured.api)
    assert captured.providers
    provider = captured.providers[0]
    assert provider["id"] == "anthropic-vertex"
    return provider


@pytest.mark.asyncio
async def test_resolves_adc_marker_through_provider_hook() -> None:
    provider = _register_provider()
    resolve_config_api_key = provider.get("resolveConfigApiKey")
    assert callable(resolve_config_api_key)
    assert resolve_config_api_key({"env": {"ANTHROPIC_VERTEX_USE_GCP_METADATA": "true"}}) == (
        "gcp-vertex-credentials"
    )


@pytest.mark.asyncio
async def test_merges_implicit_vertex_catalog_into_explicit_provider_overrides() -> None:
    with patch(
        "openclaw_extensions.anthropic_vertex.index.has_anthropic_vertex_available_auth",
        return_value=True,
    ):
        provider = _register_provider()
        catalog = provider.get("catalog")
        assert catalog is not None
        result = await catalog["run"](
            {
                "config": {
                    "models": {
                        "providers": {
                            "anthropic-vertex": {
                                "baseUrl": "https://europe-west4-aiplatform.googleapis.com",
                                "headers": {"x-test-header": "1"},
                            }
                        }
                    }
                },
                "env": {
                    "ANTHROPIC_VERTEX_USE_GCP_METADATA": "true",
                    "GOOGLE_CLOUD_LOCATION": "us-east5",
                },
            }
        )

    assert result is not None and "provider" in result
    merged = result["provider"]
    assert merged["api"] == "anthropic-messages"
    assert merged["apiKey"] == "gcp-vertex-credentials"
    assert merged["baseUrl"] == "https://europe-west4-aiplatform.googleapis.com"
    assert merged["headers"] == {"x-test-header": "1"}
    assert [model["id"] for model in merged["models"]] == [
        "claude-fable-5",
        "claude-opus-4-8",
        "claude-opus-4-6",
        "claude-sonnet-4-6",
    ]
    assert merged["models"][0]["thinkingLevelMap"] == {
        "off": "low",
        "minimal": "low",
        "xhigh": "xhigh",
        "max": "max",
    }
    assert merged["models"][2]["thinkingLevelMap"] == {"xhigh": None, "max": "max"}
    assert merged["models"][3]["thinkingLevelMap"] == {"xhigh": None, "max": "max"}


def test_owns_anthropic_style_replay_policy() -> None:
    provider = _register_provider()
    build_replay_policy = provider.get("buildReplayPolicy")
    assert callable(build_replay_policy)
    assert build_replay_policy(
        {
            "provider": "anthropic-vertex",
            "modelApi": "anthropic-messages",
            "modelId": "claude-sonnet-4-6",
        }
    ) == {
        "sanitizeMode": "full",
        "sanitizeToolCallIds": True,
        "toolCallIdMode": "strict",
        "preserveNativeAnthropicToolUseIds": True,
        "preserveSignatures": True,
        "repairToolUseResultPairing": True,
        "validateAnthropicTurns": True,
        "allowSyntheticToolResults": True,
    }
    fable_policy = build_replay_policy(
        {
            "provider": "anthropic-vertex",
            "modelApi": "anthropic-messages",
            "modelId": "claude-fable-5",
        }
    )
    assert "dropThinkingBlocks" not in fable_policy


def test_owns_anthropic_style_thinking_policy() -> None:
    provider = _register_provider()
    resolve_thinking_profile = provider.get("resolveThinkingProfile")
    assert callable(resolve_thinking_profile)

    opus_profile = resolve_thinking_profile(
        {"provider": "anthropic-vertex", "modelId": "claude-opus-4-8"}
    )
    assert opus_profile is not None
    assert opus_profile["defaultLevel"] == "off"
    assert "max" in [level["id"] for level in opus_profile["levels"]]

    fable_profile = resolve_thinking_profile(
        {"provider": "anthropic-vertex", "modelId": "claude-fable-5"}
    )
    assert fable_profile is not None
    assert fable_profile["defaultLevel"] == "high"
    assert fable_profile["preserveWhenCatalogReasoningFalse"] is True

    alias_profile = resolve_thinking_profile(
        {
            "provider": "anthropic-vertex",
            "modelId": "production-claude",
            "params": {"canonicalModelId": "claude-fable-5"},
        }
    )
    assert alias_profile is not None
    assert alias_profile["defaultLevel"] == "high"


def test_restores_fable_metadata_for_explicit_vertex_catalog_rows() -> None:
    provider = _register_provider()
    normalize_resolved_model = provider.get("normalizeResolvedModel")
    assert callable(normalize_resolved_model)

    normalized = normalize_resolved_model(
        {
            "provider": "anthropic-vertex",
            "modelId": "claude-fable-5",
            "model": {
                "id": "claude-fable-5",
                "name": "Claude Fable 5",
                "api": "anthropic-messages",
                "provider": "anthropic-vertex",
                "baseUrl": "https://aiplatform.googleapis.com",
                "reasoning": False,
                "input": ["text"],
                "cost": {"input": 10, "output": 50, "cacheRead": 1, "cacheWrite": 12.5},
                "contextWindow": 200_000,
                "maxTokens": 8192,
            },
        }
    )
    assert normalized == {
        "id": "claude-fable-5",
        "name": "Claude Fable 5",
        "api": "anthropic-messages",
        "provider": "anthropic-vertex",
        "baseUrl": "https://aiplatform.googleapis.com",
        "reasoning": True,
        "input": ["text", "image"],
        "cost": {"input": 10, "output": 50, "cacheRead": 1, "cacheWrite": 12.5},
        "contextWindow": 1_000_000,
        "contextTokens": 1_000_000,
        "maxTokens": 128_000,
        "thinkingLevelMap": {
            "off": "low",
            "minimal": "low",
            "xhigh": "xhigh",
            "max": "max",
        },
    }

    alias_normalized = normalize_resolved_model(
        {
            "provider": "anthropic-vertex",
            "modelId": "production-claude",
            "model": {
                "id": "production-claude",
                "name": "Production Claude",
                "api": "anthropic-messages",
                "provider": "anthropic-vertex",
                "baseUrl": "https://aiplatform.googleapis.com",
                "reasoning": False,
                "input": ["text"],
                "cost": {"input": 10, "output": 50, "cacheRead": 1, "cacheWrite": 12.5},
                "contextWindow": 200_000,
                "maxTokens": 8192,
                "params": {"canonicalModelId": "claude-fable-5"},
                "thinkingLevelMap": {"max": None},
            },
        }
    )
    assert alias_normalized is not None
    assert alias_normalized["reasoning"] is True
    assert alias_normalized["input"] == ["text", "image"]
    assert alias_normalized["contextWindow"] == 1_000_000
    assert alias_normalized["maxTokens"] == 128_000
    assert alias_normalized["thinkingLevelMap"] == {
        "off": "low",
        "minimal": "low",
        "xhigh": "xhigh",
        "max": None,
    }


def test_resolves_synthetic_auth_when_adc_is_available() -> None:
    with patch(
        "openclaw_extensions.anthropic_vertex.index.has_anthropic_vertex_available_auth",
        return_value=True,
    ):
        provider = _register_provider()
        resolve_synthetic_auth = provider.get("resolveSyntheticAuth")
        assert callable(resolve_synthetic_auth)
        assert resolve_synthetic_auth(
            {
                "provider": "anthropic-vertex",
                "config": None,
                "providerConfig": None,
            }
        ) == {
            "apiKey": "gcp-vertex-credentials",
            "source": "gcp-vertex-credentials (ADC)",
            "mode": "api-key",
        }


def test_returns_undefined_when_adc_is_not_available() -> None:
    with patch(
        "openclaw_extensions.anthropic_vertex.index.has_anthropic_vertex_available_auth",
        return_value=False,
    ):
        provider = _register_provider()
        resolve_synthetic_auth = provider.get("resolveSyntheticAuth")
        assert callable(resolve_synthetic_auth)
        assert (
            resolve_synthetic_auth(
                {
                    "provider": "anthropic-vertex",
                    "config": None,
                    "providerConfig": None,
                }
            )
            is None
        )
