"""Tests for the Copilot Proxy provider extension."""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from openclaw.plugin_sdk.plugin_test_runtime import create_captured_plugin_registration
from openclaw_extensions.copilot_proxy import index, runtime_api

EXTENSION_ROOT = Path(__file__).resolve().parents[2] / "openclaw_extensions" / "copilot_proxy"


def test_runtime_api_reexports_define_plugin_entry() -> None:
    from openclaw.plugin_sdk.plugin_entry import define_plugin_entry as core_define_plugin_entry

    assert runtime_api.define_plugin_entry is core_define_plugin_entry
    assert runtime_api.OpenClawPluginApi is not None


def test_plugin_entry_metadata() -> None:
    entry = index.default
    assert entry.id == "copilot-proxy"
    assert entry.name == "Copilot Proxy"
    assert "VS Code LM" in entry.description
    assert callable(entry.register)
    assert entry.config_schema is not None
    assert callable(entry.config_schema["safeParse"])


def test_manifest_matches_entry() -> None:
    manifest = json.loads((EXTENSION_ROOT / "openclaw.plugin.json").read_text(encoding="utf-8"))
    entry = index.default

    assert manifest["id"] == entry.id
    assert manifest["providers"] == ["copilot-proxy"]
    assert manifest["providerAuthChoices"] == [
        {
            "provider": "copilot-proxy",
            "method": "local",
            "choiceId": "copilot-proxy",
            "choiceLabel": "Copilot Proxy",
            "choiceHint": "Configure base URL + model ids",
            "groupId": "copilot",
            "groupLabel": "Copilot",
            "groupHint": "GitHub + local proxy",
        }
    ]


def test_registers_copilot_proxy_provider() -> None:
    captured = create_captured_plugin_registration(id="copilot-proxy")
    index.default.register(captured.api)

    assert len(captured.providers) == 1
    provider = captured.providers[0]
    assert provider["id"] == "copilot-proxy"
    assert provider["label"] == "Copilot Proxy"
    assert provider["docsPath"] == "/providers/models"
    assert provider["wizard"] == {
        "setup": {
            "choiceId": "copilot-proxy",
            "choiceLabel": "Copilot Proxy",
            "choiceHint": "Configure base URL + model ids",
            "methodId": "local",
        },
    }

    assert len(provider["auth"]) == 1
    auth_method = provider["auth"][0]
    assert auth_method == {
        "id": "local",
        "label": "Local proxy",
        "hint": "Configure base URL + models for the Copilot Proxy server",
        "kind": "custom",
        "run": auth_method["run"],
    }
    assert inspect.iscoroutinefunction(auth_method["run"])


@pytest.mark.asyncio
async def test_local_auth_flow_builds_config_patch() -> None:
    captured = create_captured_plugin_registration(id="copilot-proxy")
    index.default.register(captured.api)
    run = captured.providers[0]["auth"][0]["run"]

    prompter = AsyncMock()
    prompter.text = AsyncMock(
        side_effect=[
            "http://localhost:4000",
            "gpt-5.2, gpt-5-mini",
        ]
    )

    result = await run({"prompter": prompter})

    assert result["defaultModel"] == "copilot-proxy/gpt-5.2"
    assert result["profiles"] == [
        {
            "profileId": "copilot-proxy:local",
            "credential": {
                "type": "token",
                "provider": "copilot-proxy",
                "token": "n/a",
            },
        }
    ]
    provider_config = result["configPatch"]["models"]["providers"]["copilot-proxy"]
    assert provider_config["baseUrl"] == "http://localhost:4000/v1"
    assert provider_config["apiKey"] == "n/a"
    assert provider_config["api"] == "openai-completions"
    assert provider_config["authHeader"] is False
    assert [model["id"] for model in provider_config["models"]] == ["gpt-5.2", "gpt-5-mini"]
    assert provider_config["models"][0] == {
        "id": "gpt-5.2",
        "name": "gpt-5.2",
        "api": "openai-completions",
        "reasoning": False,
        "input": ["text", "image"],
        "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
        "contextWindow": 128_000,
        "maxTokens": 8192,
    }
    assert result["configPatch"]["agents"]["defaults"]["models"] == {
        "copilot-proxy/gpt-5.2": {},
        "copilot-proxy/gpt-5-mini": {},
    }
    assert result["notes"] == [
        "Start the Copilot Proxy VS Code extension before using these models.",
        "Copilot Proxy serves /v1/chat/completions; base URL must include /v1.",
        (
            "Model availability depends on your Copilot plan; "
            "edit models.providers.copilot-proxy if needed."
        ),
    ]


@pytest.mark.asyncio
async def test_local_auth_uses_default_base_url_and_models_when_prompts_are_empty() -> None:
    captured = create_captured_plugin_registration(id="copilot-proxy")
    index.default.register(captured.api)
    run = captured.providers[0]["auth"][0]["run"]

    prompter = AsyncMock()
    prompter.text = AsyncMock(side_effect=["", ""])

    result = await run({"prompter": prompter})
    provider_config = result["configPatch"]["models"]["providers"]["copilot-proxy"]

    assert provider_config["baseUrl"] == index.DEFAULT_BASE_URL
    assert result["defaultModel"] == f"copilot-proxy/{index.DEFAULT_MODEL_IDS[0]}"
    assert len(provider_config["models"]) == 0


def test_normalize_base_url_and_model_parsing_helpers() -> None:
    assert index._normalize_base_url("http://localhost:4000/") == "http://localhost:4000/v1"
    assert index._normalize_base_url("  ") == index.DEFAULT_BASE_URL
    assert index._validate_base_url("not-a-url") == "Enter a valid URL"
    assert index._validate_base_url("http://localhost:3000") is None
    assert index._parse_model_ids("gpt-5.2,\ngpt-5-mini, gpt-5.2") == ["gpt-5.2", "gpt-5-mini"]
