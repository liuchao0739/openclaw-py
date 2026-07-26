"""Tests for the Cerebras provider extension."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from openclaw.plugin_sdk.plugin_test_runtime import create_captured_plugin_registration
from openclaw.plugin_sdk.provider_onboard import resolve_agent_model_primary_value
from openclaw_extensions.cerebras.api import (
    CEREBRAS_BASE_URL,
    CEREBRAS_DEFAULT_MODEL_REF,
    CEREBRAS_MODEL_CATALOG,
    apply_cerebras_config,
    build_cerebras_catalog_models,
    build_cerebras_model_definition,
    build_cerebras_provider,
)
from openclaw_extensions.cerebras.index import default as cerebras_plugin

_MANIFEST_PATH = (
    Path(__file__).resolve().parents[2]
    / "openclaw_extensions"
    / "cerebras"
    / "openclaw.plugin.json"
)


def _read_manifest() -> dict[str, Any]:
    return json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))


def test_registers_the_manifest_owned_api_key_onboarding_flow() -> None:
    captured = create_captured_plugin_registration(id="cerebras")
    cerebras_plugin.register(captured.api)
    assert captured.providers, "expected Cerebras provider registration"
    provider = captured.providers[0]

    assert [method.get("wizard", {}).get("choiceId") for method in provider.get("auth", [])] == [
        "cerebras-api-key"
    ]
    assert provider["id"] == "cerebras"
    assert provider["envVars"] == ["CEREBRAS_API_KEY"]
    assert provider["auth"][0]["id"] == "api-key"
    assert provider["auth"][0]["kind"] == "api_key"
    assert provider["auth"][0]["wizard"]["choiceId"] == "cerebras-api-key"
    assert provider["catalog"]["buildProvider"] is build_cerebras_provider
    assert provider["catalog"]["buildStaticProvider"] is build_cerebras_provider
    assert provider["applyConfig"] is apply_cerebras_config

    manifest = _read_manifest()
    assert manifest["providerAuthChoices"] == [
        {
            "provider": "cerebras",
            "method": "api-key",
            "choiceId": "cerebras-api-key",
            "choiceLabel": "Cerebras API key",
            "groupId": "cerebras",
            "groupLabel": "Cerebras",
            "groupHint": "Fast OpenAI-compatible inference",
            "optionKey": "cerebrasApiKey",
            "cliFlag": "--cerebras-api-key",
            "cliOption": "--cerebras-api-key <key>",
            "cliDescription": "Cerebras API key",
        }
    ]
    assert manifest["setup"]["providers"] == [{"id": "cerebras", "envVars": ["CEREBRAS_API_KEY"]}]


def test_exposes_the_static_cerebras_catalog() -> None:
    provider = build_cerebras_provider()

    assert provider["baseUrl"] == "https://api.cerebras.ai/v1"
    assert provider["api"] == "openai-completions"
    assert [model["id"] for model in provider["models"]] == [
        "zai-glm-4.7",
        "gpt-oss-120b",
        "qwen-3-235b-a22b-instruct-2507",
        "llama3.1-8b",
    ]
    assert provider["models"][0] == {
        "id": "zai-glm-4.7",
        "name": "Z.ai GLM 4.7",
        "reasoning": True,
        "input": ["text"],
        "cost": {
            "input": 2.25,
            "output": 2.75,
            "cacheRead": 2.25,
            "cacheWrite": 2.75,
        },
        "contextWindow": 128000,
        "maxTokens": 8192,
    }


def test_manifest_constants_match_catalog_helpers() -> None:
    assert CEREBRAS_BASE_URL == "https://api.cerebras.ai/v1"
    assert CEREBRAS_DEFAULT_MODEL_REF == "cerebras/zai-glm-4.7"
    assert len(CEREBRAS_MODEL_CATALOG) == 4
    assert {model["id"] for model in CEREBRAS_MODEL_CATALOG} == {
        "zai-glm-4.7",
        "gpt-oss-120b",
        "qwen-3-235b-a22b-instruct-2507",
        "llama3.1-8b",
    }
    assert len(build_cerebras_catalog_models()) == len(CEREBRAS_MODEL_CATALOG)


def test_build_cerebras_model_definition_normalizes_one_manifest_entry() -> None:
    model = CEREBRAS_MODEL_CATALOG[0]
    defined = build_cerebras_model_definition(model)

    assert defined["id"] == model["id"]
    assert defined["name"] == model["name"]
    assert defined["reasoning"] is True
    assert defined["contextWindow"] == 128000
    assert defined["maxTokens"] == 8192


def test_registers_the_manifest_catalog_through_the_onboarding_preset() -> None:
    result = apply_cerebras_config({})
    provider = result.get("models", {}).get("providers", {}).get("cerebras")

    assert provider == {
        "baseUrl": CEREBRAS_BASE_URL,
        "api": "openai-completions",
        "models": build_cerebras_catalog_models(),
    }


def test_sets_cerebras_only_when_there_is_no_primary_model() -> None:
    existing = {
        "agents": {
            "defaults": {
                "model": {"primary": "openai/gpt-5.5"},
            }
        }
    }

    result = apply_cerebras_config(existing)

    assert (
        resolve_agent_model_primary_value(result["agents"]["defaults"]["model"]) == "openai/gpt-5.5"
    )
    assert result["agents"]["defaults"]["models"][CEREBRAS_DEFAULT_MODEL_REF] == {
        "alias": "Cerebras GLM 4.7",
    }


def test_uses_cerebras_as_the_first_configured_primary_model() -> None:
    result = apply_cerebras_config({})

    assert resolve_agent_model_primary_value(result["agents"]["defaults"]["model"]) == (
        CEREBRAS_DEFAULT_MODEL_REF
    )
