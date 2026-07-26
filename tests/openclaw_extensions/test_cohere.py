"""Tests for the Cohere provider extension."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from openclaw.plugin_sdk.plugin_test_runtime import create_captured_plugin_registration
from openclaw.plugin_sdk.provider_onboard import resolve_agent_model_primary_value
from openclaw_extensions.cohere.index import default as cohere_plugin
from openclaw_extensions.cohere.models import (
    COHERE_BASE_URL,
    COHERE_MODEL_CATALOG,
    build_cohere_catalog_models,
)
from openclaw_extensions.cohere.onboard import (
    COHERE_DEFAULT_MODEL_ID,
    COHERE_DEFAULT_MODEL_REF,
    apply_cohere_config,
)
from openclaw_extensions.cohere.provider_catalog import build_cohere_provider
from openclaw_extensions.cohere.stream import create_cohere_completions_wrapper

_MANIFEST_PATH = (
    Path(__file__).resolve().parents[2] / "openclaw_extensions" / "cohere" / "openclaw.plugin.json"
)


def _read_manifest() -> dict[str, Any]:
    return json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))


def _require_cohere_model() -> dict[str, Any]:
    models = build_cohere_provider().get("models") or []
    if not models:
        raise AssertionError("Cohere catalog did not provide a model")
    return models[0]


def _capture_cohere_payload(context: dict[str, Any]) -> dict[str, Any]:
    captured: dict[str, Any] = {}

    def base_stream_fn(model: Any, stream_context: dict[str, Any], options: dict[str, Any] | None):
        payload: dict[str, Any] = {
            "messages": [
                {
                    "role": "system",
                    "content": stream_context.get("systemPrompt", "system"),
                }
            ],
            "max_tokens": 2048,
            "tool_choice": "auto",
        }
        if options and options.get("onPayload"):
            options["onPayload"](payload, model)
        return {}

    wrapped_stream_fn = create_cohere_completions_wrapper(base_stream_fn)
    wrapped_stream_fn(
        _require_cohere_model(),
        context,
        {
            "onPayload": lambda payload, _model: captured.update(payload),
        },
    )
    if not captured:
        raise AssertionError("Cohere payload was not captured")
    return captured


def test_registers_the_manifest_owned_api_key_onboarding_flow() -> None:
    captured = create_captured_plugin_registration(id="cohere")
    cohere_plugin.register(captured.api)
    assert captured.providers, "expected Cohere provider registration"
    provider = captured.providers[0]

    assert [method.get("wizard", {}).get("choiceId") for method in provider.get("auth", [])] == [
        "cohere-api-key"
    ]
    assert provider["id"] == "cohere"
    assert provider["envVars"] == ["COHERE_API_KEY"]
    assert provider["auth"][0]["id"] == "api-key"
    assert provider["auth"][0]["kind"] == "api_key"
    assert provider["auth"][0]["wizard"]["choiceId"] == "cohere-api-key"

    manifest = _read_manifest()
    assert manifest["providerAuthChoices"] == [
        {
            "provider": "cohere",
            "method": "api-key",
            "choiceId": "cohere-api-key",
            "choiceLabel": "Cohere API key",
            "groupId": "cohere",
            "groupLabel": "Cohere",
            "groupHint": "OpenAI-compatible inference",
            "optionKey": "cohereApiKey",
            "cliFlag": "--cohere-api-key",
            "cliOption": "--cohere-api-key <key>",
            "cliDescription": "Cohere API key",
        }
    ]
    assert manifest["setup"]["providers"] == [{"id": "cohere", "envVars": ["COHERE_API_KEY"]}]


def test_exposes_the_static_cohere_catalog() -> None:
    provider = build_cohere_provider()

    assert provider["baseUrl"] == "https://api.cohere.ai/compatibility/v1"
    assert provider["api"] == "openai-completions"
    assert provider["models"] == [
        {
            "id": "command-a-03-2025",
            "name": "Command A",
            "reasoning": False,
            "input": ["text"],
            "cost": {
                "input": 2.5,
                "output": 10.0,
                "cacheRead": 0,
                "cacheWrite": 0,
            },
            "contextWindow": 256000,
            "maxTokens": 8000,
            "compat": {
                "supportsStore": False,
                "supportsUsageInStreaming": False,
                "maxTokensField": "max_tokens",
            },
        }
    ]


def test_uses_cohere_openai_compatible_completions_payload_fields() -> None:
    params = _capture_cohere_payload(
        {
            "systemPrompt": "system",
            "messages": [],
            "tools": [
                {
                    "name": "lookup",
                    "description": "Look up a value",
                    "parameters": {"type": "object", "properties": {}},
                }
            ],
        }
    )

    assert params["max_tokens"] == 2048
    assert "max_completion_tokens" not in params
    assert "store" not in params
    assert "stream_options" not in params
    assert "tool_choice" not in params
    assert {"role": "developer", "content": "system"} in params["messages"]
    assert not any(message.get("role") == "system" for message in params["messages"])


def test_registers_the_manifest_catalog_through_the_onboarding_preset() -> None:
    result = apply_cohere_config({})
    provider = result.get("models", {}).get("providers", {}).get("cohere")

    assert provider == {
        "baseUrl": COHERE_BASE_URL,
        "api": "openai-completions",
        "models": build_cohere_catalog_models(),
    }
    assert [model["id"] for model in provider["models"]] == [COHERE_DEFAULT_MODEL_ID]
    assert len(build_cohere_catalog_models()) == len(COHERE_MODEL_CATALOG)


def test_sets_cohere_only_when_there_is_no_primary_model() -> None:
    existing = {
        "agents": {
            "defaults": {
                "model": {"primary": "openai/gpt-5.5"},
            }
        }
    }

    result = apply_cohere_config(existing)

    assert (
        resolve_agent_model_primary_value(result["agents"]["defaults"]["model"]) == "openai/gpt-5.5"
    )
    assert result["agents"]["defaults"]["models"][COHERE_DEFAULT_MODEL_REF] == {
        "alias": "Cohere Command A",
    }


def test_uses_cohere_as_the_first_configured_primary_model() -> None:
    result = apply_cohere_config({})

    assert resolve_agent_model_primary_value(result["agents"]["defaults"]["model"]) == (
        COHERE_DEFAULT_MODEL_REF
    )
