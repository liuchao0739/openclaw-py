"""Tests for the DeepSeek provider policy API."""

from __future__ import annotations

from typing import Any

from openclaw_extensions.deepseek.provider_policy_api import (
    normalize_config,
    resolve_thinking_profile,
)


def test_advertises_max_thinking_levels_for_deep_seek_v4_models() -> None:
    expected_v4_levels = ["off", "minimal", "low", "medium", "high", "xhigh", "max"]

    pro_profile = resolve_thinking_profile({"provider": "deepseek", "modelId": "deepseek-v4-pro"})
    assert pro_profile is not None
    assert [level["id"] for level in pro_profile["levels"]] == expected_v4_levels

    flash_profile = resolve_thinking_profile(
        {"provider": "deepseek", "modelId": "deepseek-v4-flash"}
    )
    assert flash_profile is not None
    assert flash_profile["defaultLevel"] == "high"

    assert resolve_thinking_profile({"provider": "deepseek", "modelId": "deepseek-chat"}) is None
    assert (
        resolve_thinking_profile({"provider": "openrouter", "modelId": "deepseek-v4-pro"}) is None
    )


def test_hydrates_context_window_and_cost_from_catalog_for_known_models() -> None:
    provider_config: dict[str, Any] = {
        "baseUrl": "https://api.deepseek.com",
        "api": "openai-completions",
        "models": [
            {
                "id": "deepseek-v4-flash",
                "name": "DeepSeek V4 Flash",
                "reasoning": True,
                "input": ["text"],
            }
        ],
    }

    result = normalize_config({"provider": "deepseek", "providerConfig": provider_config})

    assert result is not provider_config
    model = result["models"][0]
    assert model["contextWindow"] == 1_000_000
    assert model["maxTokens"] == 384_000
    assert model["cost"] == {
        "input": 0.14,
        "output": 0.28,
        "cacheRead": 0.028,
        "cacheWrite": 0,
    }


def test_hydrates_deep_seek_v4_pro_with_correct_metadata() -> None:
    provider_config: dict[str, Any] = {
        "baseUrl": "https://api.deepseek.com",
        "api": "openai-completions",
        "models": [
            {
                "id": "deepseek-v4-pro",
                "name": "DeepSeek V4 Pro",
                "reasoning": True,
                "input": ["text"],
            }
        ],
    }

    result = normalize_config({"provider": "deepseek", "providerConfig": provider_config})
    model = result["models"][0]
    assert model["contextWindow"] == 1_000_000
    assert model["maxTokens"] == 384_000
    assert model["cost"] == {
        "input": 1.74,
        "output": 3.48,
        "cacheRead": 0.145,
        "cacheWrite": 0,
    }


def test_hydrates_deep_seek_chat_with_131k_context() -> None:
    provider_config: dict[str, Any] = {
        "baseUrl": "https://api.deepseek.com",
        "api": "openai-completions",
        "models": [
            {
                "id": "deepseek-chat",
                "name": "DeepSeek Chat",
                "reasoning": False,
                "input": ["text"],
            }
        ],
    }

    result = normalize_config({"provider": "deepseek", "providerConfig": provider_config})
    assert result["models"][0]["contextWindow"] == 131_072


def test_preserves_explicit_user_context_window_override() -> None:
    provider_config: dict[str, Any] = {
        "baseUrl": "https://api.deepseek.com",
        "api": "openai-completions",
        "models": [
            {
                "id": "deepseek-v4-flash",
                "name": "DeepSeek V4 Flash",
                "reasoning": True,
                "input": ["text"],
                "contextWindow": 500_000,
            }
        ],
    }

    result = normalize_config({"provider": "deepseek", "providerConfig": provider_config})
    model = result["models"][0]
    assert model["contextWindow"] == 500_000
    assert model["cost"] == {
        "input": 0.14,
        "output": 0.28,
        "cacheRead": 0.028,
        "cacheWrite": 0,
    }


def test_preserves_explicit_user_cost_override() -> None:
    user_cost = {"input": 99, "output": 99, "cacheRead": 99, "cacheWrite": 99}
    provider_config: dict[str, Any] = {
        "baseUrl": "https://api.deepseek.com",
        "api": "openai-completions",
        "models": [
            {
                "id": "deepseek-v4-flash",
                "name": "DeepSeek V4 Flash",
                "reasoning": True,
                "input": ["text"],
                "cost": user_cost,
            }
        ],
    }

    result = normalize_config({"provider": "deepseek", "providerConfig": provider_config})
    model = result["models"][0]
    assert model["cost"] == user_cost
    assert model["contextWindow"] == 1_000_000


def test_preserves_explicit_user_max_tokens_override() -> None:
    provider_config: dict[str, Any] = {
        "baseUrl": "https://api.deepseek.com",
        "api": "openai-completions",
        "models": [
            {
                "id": "deepseek-v4-flash",
                "name": "DeepSeek V4 Flash",
                "reasoning": True,
                "input": ["text"],
                "maxTokens": 100_000,
            }
        ],
    }

    result = normalize_config({"provider": "deepseek", "providerConfig": provider_config})
    assert result["models"][0]["maxTokens"] == 100_000


def test_returns_provider_config_unchanged_when_all_models_already_have_metadata() -> None:
    provider_config: dict[str, Any] = {
        "baseUrl": "https://api.deepseek.com",
        "api": "openai-completions",
        "models": [
            {
                "id": "deepseek-v4-flash",
                "name": "DeepSeek V4 Flash",
                "reasoning": True,
                "input": ["text"],
                "contextWindow": 1_000_000,
                "maxTokens": 384_000,
                "cost": {"input": 0.14, "output": 0.28, "cacheRead": 0.028, "cacheWrite": 0},
            }
        ],
    }

    result = normalize_config({"provider": "deepseek", "providerConfig": provider_config})
    assert result is provider_config


def test_passes_through_unknown_model_ids_unchanged() -> None:
    provider_config: dict[str, Any] = {
        "baseUrl": "https://api.deepseek.com",
        "api": "openai-completions",
        "models": [
            {
                "id": "deepseek-custom-finetune",
                "name": "Custom Fine-tune",
                "reasoning": False,
                "input": ["text"],
            }
        ],
    }

    result = normalize_config({"provider": "deepseek", "providerConfig": provider_config})
    assert result is provider_config


def test_returns_provider_config_unchanged_when_models_array_is_empty() -> None:
    provider_config: dict[str, Any] = {
        "baseUrl": "https://api.deepseek.com",
        "api": "openai-completions",
        "models": [],
    }

    result = normalize_config({"provider": "deepseek", "providerConfig": provider_config})
    assert result is provider_config


def test_hydrates_only_the_models_that_need_it_in_a_mixed_list() -> None:
    provider_config: dict[str, Any] = {
        "baseUrl": "https://api.deepseek.com",
        "api": "openai-completions",
        "models": [
            {
                "id": "deepseek-v4-flash",
                "name": "DeepSeek V4 Flash",
                "reasoning": True,
                "input": ["text"],
                "contextWindow": 1_000_000,
                "maxTokens": 384_000,
                "cost": {"input": 0.14, "output": 0.28, "cacheRead": 0.028, "cacheWrite": 0},
            },
            {
                "id": "deepseek-v4-pro",
                "name": "DeepSeek V4 Pro",
                "reasoning": True,
                "input": ["text"],
            },
        ],
    }

    result = normalize_config({"provider": "deepseek", "providerConfig": provider_config})
    assert result is not provider_config
    assert result["models"][0] is provider_config["models"][0]
    assert result["models"][1]["contextWindow"] == 1_000_000
    assert result["models"][1]["cost"] == {
        "input": 1.74,
        "output": 3.48,
        "cacheRead": 0.145,
        "cacheWrite": 0,
    }
