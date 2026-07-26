"""Tests for Codex provider plugin."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from openclaw_extensions.codex.prompt_overlay import CODEX_GPT5_BEHAVIOR_CONTRACT
from openclaw_extensions.codex.provider import build_codex_provider, build_codex_provider_catalog
from openclaw_extensions.codex.provider_discovery import codex_provider_discovery


def _expect_static_fallback_catalog(result: dict[str, Any]) -> None:
    assert [model["id"] for model in result["provider"]["models"]] == ["gpt-5.5", "gpt-5.4-mini"]


@pytest.mark.asyncio
async def test_maps_codex_app_server_models_to_a_codex_provider_catalog() -> None:
    list_models = AsyncMock(
        return_value={
            "models": [
                {
                    "id": "gpt-5.4",
                    "model": "gpt-5.4",
                    "displayName": "gpt-5.4",
                    "hidden": False,
                    "inputModalities": ["text", "image"],
                    "supportedReasoningEfforts": ["low", "medium", "high", "xhigh"],
                },
                {
                    "id": "hidden-model",
                    "model": "hidden-model",
                    "hidden": True,
                    "inputModalities": ["text"],
                    "supportedReasoningEfforts": [],
                },
            ]
        }
    )

    result = await build_codex_provider_catalog(
        {
            "env": {},
            "listModels": list_models,
            "pluginConfig": {"discovery": {"timeoutMs": 1234}},
        }
    )

    list_models.assert_awaited_once()
    call_kwargs = list_models.await_args.kwargs
    assert call_kwargs["limit"] == 100
    assert call_kwargs["timeoutMs"] == 1234
    assert call_kwargs["sharedClient"] is False
    assert result["provider"]["auth"] == "token"
    assert result["provider"]["api"] == "openai-chatgpt-responses"
    assert len(result["provider"]["models"]) == 1
    model = result["provider"]["models"][0]
    assert model["id"] == "gpt-5.4"
    assert model["name"] == "gpt-5.4"
    assert model["reasoning"] is True
    assert model["input"] == ["text", "image"]
    assert model["compat"] == {
        "supportsReasoningEffort": True,
        "supportsUsageInStreaming": True,
    }


@pytest.mark.asyncio
async def test_keeps_a_static_fallback_catalog_when_discovery_is_disabled() -> None:
    list_models = AsyncMock()
    result = await build_codex_provider_catalog(
        {
            "env": {},
            "listModels": list_models,
            "pluginConfig": {"discovery": {"enabled": False}},
        }
    )
    list_models.assert_not_awaited()
    _expect_static_fallback_catalog(result)


@pytest.mark.asyncio
async def test_uses_live_plugin_config_to_re_enable_discovery_after_startup_disable() -> None:
    list_models = AsyncMock(
        return_value={
            "models": [
                {
                    "id": "gpt-5.4",
                    "model": "gpt-5.4",
                    "displayName": "gpt-5.4",
                    "hidden": False,
                    "inputModalities": ["text", "image"],
                    "supportedReasoningEfforts": ["low", "medium", "high", "xhigh"],
                }
            ]
        }
    )
    provider = build_codex_provider(
        {"pluginConfig": {"discovery": {"enabled": False}}, "listModels": list_models}
    )
    result = await provider["catalog"]["run"](
        {
            "config": {
                "plugins": {
                    "entries": {
                        "codex": {
                            "config": {
                                "discovery": {
                                    "enabled": True,
                                    "timeoutMs": 4321,
                                }
                            }
                        }
                    }
                }
            },
            "env": {},
        }
    )
    call_kwargs = list_models.await_args.kwargs
    assert call_kwargs["timeoutMs"] == 4321
    assert [model["id"] for model in result["provider"]["models"]] == ["gpt-5.4"]


@pytest.mark.asyncio
async def test_pages_through_live_discovery_before_building_the_provider_catalog() -> None:
    list_models = AsyncMock(
        side_effect=[
            {
                "models": [
                    {
                        "id": "gpt-5.4",
                        "model": "gpt-5.4",
                        "hidden": False,
                        "inputModalities": ["text", "image"],
                        "supportedReasoningEfforts": ["medium"],
                    }
                ],
                "nextCursor": "page-2",
            },
            {
                "models": [
                    {
                        "id": "gpt-5.5",
                        "model": "gpt-5.5",
                        "hidden": False,
                        "inputModalities": ["text"],
                        "supportedReasoningEfforts": [],
                    }
                ]
            },
        ]
    )
    result = await build_codex_provider_catalog({"env": {}, "listModels": list_models})
    assert list_models.await_args_list[0].kwargs["cursor"] is None
    assert list_models.await_args_list[1].kwargs["cursor"] == "page-2"
    assert [model["id"] for model in result["provider"]["models"]] == ["gpt-5.4", "gpt-5.5"]


@pytest.mark.asyncio
async def test_reports_discovery_failures_before_using_the_fallback_catalog() -> None:
    error = RuntimeError("app-server down")
    on_discovery_failure = Mock()
    list_models = AsyncMock(side_effect=error)

    result = await build_codex_provider_catalog(
        {
            "env": {},
            "listModels": list_models,
            "onDiscoveryFailure": on_discovery_failure,
        }
    )

    on_discovery_failure.assert_called_once_with(error)
    _expect_static_fallback_catalog(result)


@pytest.mark.asyncio
async def test_keeps_a_static_fallback_catalog_when_live_discovery_is_explicitly_disabled_by_env() -> (
    None
):
    list_models = AsyncMock()
    result = await build_codex_provider_catalog(
        {
            "env": {"OPENCLAW_CODEX_DISCOVERY_LIVE": "0"},
            "listModels": list_models,
        }
    )
    list_models.assert_not_awaited()
    _expect_static_fallback_catalog(result)


def test_resolves_arbitrary_codex_app_server_model_ids_as_text_only_until_discovered() -> None:
    provider = build_codex_provider()
    model = provider["resolveDynamicModel"]({"provider": "codex", "modelId": " custom-model "})
    assert model == {
        "id": "custom-model",
        "name": "custom-model",
        "api": "openai-chatgpt-responses",
        "reasoning": False,
        "input": ["text"],
        "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
        "contextWindow": 272_000,
        "maxTokens": 128_000,
        "compat": {"supportsReasoningEffort": False, "supportsUsageInStreaming": True},
        "provider": "codex",
        "baseUrl": "https://chatgpt.com/backend-api",
    }


def test_keeps_fallback_codex_app_server_models_image_capable() -> None:
    provider = build_codex_provider()
    model = provider["resolveDynamicModel"]({"provider": "codex", "modelId": "gpt-5.5"})
    assert model["id"] == "gpt-5.5"
    assert model["input"] == ["text", "image"]


def test_treats_o4_ids_as_reasoning_capable_codex_models() -> None:
    provider = build_codex_provider()
    model = provider["resolveDynamicModel"]({"provider": "codex", "modelId": "o4-mini"})
    assert model["id"] == "o4-mini"
    assert model["reasoning"] is True
    assert model["compat"] == {
        "supportsReasoningEffort": True,
        "supportsUsageInStreaming": True,
    }
    levels = provider["resolveThinkingProfile"]({"provider": "codex", "modelId": "o4-mini"})[
        "levels"
    ]
    assert any(level["id"] == "xhigh" for level in levels)


def test_declares_synthetic_auth_because_the_harness_owns_codex_credentials() -> None:
    provider = build_codex_provider()
    assert provider["resolveSyntheticAuth"]({"provider": "codex"}) == {
        "apiKey": "codex-app-server",
        "source": "codex-app-server",
        "mode": "token",
    }


@pytest.mark.asyncio
async def test_fetches_usage_from_native_codex_app_server_rate_limits_for_synthetic_auth() -> None:
    read_rate_limits = AsyncMock(
        return_value={
            "rateLimitsByLimitId": {
                "codex": {
                    "limitId": "codex",
                    "primary": {
                        "usedPercent": 9,
                        "windowDurationMins": 300,
                        "resetsAt": 1_700_003_600,
                    },
                }
            }
        }
    )
    provider = build_codex_provider({"readRateLimits": read_rate_limits})
    result = await provider["fetchUsageSnapshot"](
        {
            "provider": "openai",
            "token": "codex-app-server",
            "timeoutMs": 3500,
            "config": {},
            "env": {},
        }
    )
    assert result == {
        "provider": "openai",
        "displayName": "OpenAI",
        "windows": [{"label": "5h", "usedPercent": 9, "resetAt": 1_700_003_600_000}],
    }


@pytest.mark.asyncio
async def test_exposes_a_setup_auth_choice_for_installing_codex_as_an_external_provider() -> None:
    provider = build_codex_provider()
    auth_choice = provider["auth"][0]
    assert auth_choice["id"] == "app-server"
    assert auth_choice["kind"] == "custom"
    assert auth_choice["wizard"]["choiceId"] == "codex"
    assert auth_choice["wizard"]["choiceLabel"] == "Codex app-server"
    assert auth_choice["wizard"]["onboardingScopes"] == ["text-inference"]
    auth_result = await auth_choice["run"]({})
    assert auth_result == {"profiles": [], "defaultModel": "codex/gpt-5.5"}


@pytest.mark.asyncio
async def test_exposes_a_lightweight_provider_discovery_entry_for_model_list_status() -> None:
    assert codex_provider_discovery["id"] == "codex"
    assert codex_provider_discovery["resolveSyntheticAuth"]({"provider": "codex"}) == {
        "apiKey": "codex-app-server",
        "source": "codex-app-server",
        "mode": "token",
    }
    result = await codex_provider_discovery["staticCatalog"]["run"](
        {
            "config": {},
            "env": {},
            "agentDir": "/tmp/openclaw-agent",
        }
    )
    assert [model["id"] for model in result["provider"]["models"]] == ["gpt-5.5", "gpt-5.4-mini"]


def test_adds_the_gpt5_prompt_overlay_to_codex_provider_runs() -> None:
    provider = build_codex_provider()
    contribution = provider["resolveSystemPromptContribution"](
        {"provider": "codex", "modelId": "gpt-5.4"}
    )
    assert contribution["stablePrefix"] == CODEX_GPT5_BEHAVIOR_CONTRACT
    interaction_style = contribution["sectionOverrides"]["interaction_style"]
    assert "Live chat tone: short, natural, human." in interaction_style
    assert "Use heartbeats to create useful proactive progress" not in interaction_style


def test_does_not_add_the_gpt5_prompt_overlay_to_non_gpt5_codex_provider_runs() -> None:
    provider = build_codex_provider()
    assert (
        provider["resolveSystemPromptContribution"]({"provider": "codex", "modelId": "o4-mini"})
        is None
    )
