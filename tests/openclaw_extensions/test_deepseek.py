"""Tests for the DeepSeek provider extension."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from openclaw.plugin_sdk.plugin_test_runtime import create_captured_plugin_registration
from openclaw.plugin_sdk.provider_onboard import resolve_agent_model_primary_value
from openclaw_extensions.deepseek import (
    DEEPSEEK_BASE_URL,
    DEEPSEEK_DEFAULT_MODEL_REF,
    DEEPSEEK_MODEL_CATALOG,
    apply_deep_seek_config,
    build_deep_seek_model_definition,
    build_deep_seek_provider,
    create_deep_seek_v4_thinking_wrapper,
    is_deep_seek_v4_model_id,
    is_deep_seek_v4_model_ref,
    resolve_deep_seek_v4_thinking_profile,
)
from openclaw_extensions.deepseek.index import default as deepseek_plugin

_MANIFEST_PATH = (
    Path(__file__).resolve().parents[2]
    / "openclaw_extensions"
    / "deepseek"
    / "openclaw.plugin.json"
)


def _read_manifest() -> dict[str, Any]:
    return json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))


def _deep_seek_v4_model(model_id: str) -> dict[str, Any]:
    return {
        "provider": "deepseek",
        "id": model_id,
        "name": "DeepSeek V4 Flash" if model_id == "deepseek-v4-flash" else "DeepSeek V4 Pro",
        "api": "openai-completions",
        "baseUrl": DEEPSEEK_BASE_URL,
        "reasoning": True,
        "input": ["text"],
        "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
        "contextWindow": 1_000_000,
        "maxTokens": 384_000,
        "compat": {
            "supportsUsageInStreaming": True,
            "supportsReasoningEffort": True,
            "maxTokensField": "max_tokens",
        },
    }


def _capture_payload(
    *,
    thinking_level: str,
    model: dict[str, Any],
    initial_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    captured: dict[str, Any] = {}

    def base_stream_fn(_model: Any, _context: dict[str, Any], options: dict[str, Any] | None):
        payload = dict(initial_payload or {})
        if options and options.get("onPayload"):
            options["onPayload"](payload, _model)
        captured.update(payload)
        return {}

    wrapped = create_deep_seek_v4_thinking_wrapper(base_stream_fn, thinking_level)
    assert wrapped is not None
    wrapped(model, {"messages": []}, {})
    return captured


def test_registers_deep_seek_with_api_key_auth_wizard_metadata() -> None:
    captured = create_captured_plugin_registration(id="deepseek")
    deepseek_plugin.register(captured.api)
    assert captured.providers, "expected DeepSeek provider registration"
    provider = captured.providers[0]

    assert provider["id"] == "deepseek"
    assert provider["label"] == "DeepSeek"
    assert provider["envVars"] == ["DEEPSEEK_API_KEY"]
    assert len(provider["auth"]) == 1
    assert provider["auth"][0]["id"] == "api-key"
    assert provider["auth"][0]["wizard"]["choiceId"] == "deepseek-api-key"

    manifest = _read_manifest()
    assert manifest["providerAuthChoices"][0]["choiceId"] == "deepseek-api-key"


def test_builds_the_static_deep_seek_model_catalog() -> None:
    catalog_provider = build_deep_seek_provider()

    assert catalog_provider["api"] == "openai-completions"
    assert catalog_provider["baseUrl"] == "https://api.deepseek.com"
    assert [model["id"] for model in catalog_provider["models"]] == [
        "deepseek-v4-flash",
        "deepseek-v4-pro",
        "deepseek-chat",
        "deepseek-reasoner",
    ]
    flash_model = next(
        model for model in catalog_provider["models"] if model["id"] == "deepseek-v4-flash"
    )
    assert flash_model["reasoning"] is True
    assert flash_model["contextWindow"] == 1_000_000
    assert flash_model["maxTokens"] == 384_000
    assert flash_model["compat"]["supportsReasoningEffort"] is True
    assert flash_model["compat"]["maxTokensField"] == "max_tokens"
    reasoner_model = next(
        model for model in catalog_provider["models"] if model["id"] == "deepseek-reasoner"
    )
    assert reasoner_model["reasoning"] is True


def test_manifest_constants_match_catalog_helpers() -> None:
    assert DEEPSEEK_BASE_URL == "https://api.deepseek.com"
    assert DEEPSEEK_DEFAULT_MODEL_REF == "deepseek/deepseek-v4-flash"
    assert len(DEEPSEEK_MODEL_CATALOG) == 4
    assert is_deep_seek_v4_model_id("deepseek-v4-flash") is True
    assert is_deep_seek_v4_model_id("DEEPSEEK-V4-PRO") is True
    assert is_deep_seek_v4_model_id("deepseek-chat") is False
    assert is_deep_seek_v4_model_ref({"provider": "deepseek", "id": "deepseek-v4-pro"}) is True
    assert is_deep_seek_v4_model_ref({"provider": "openai", "id": "deepseek-v4-pro"}) is False


def test_build_deep_seek_model_definition_adds_openai_completions_api() -> None:
    model = DEEPSEEK_MODEL_CATALOG[0]
    defined = build_deep_seek_model_definition(model)
    assert defined["api"] == "openai-completions"
    assert defined["id"] == model["id"]


def test_registers_the_manifest_catalog_through_the_onboarding_preset() -> None:
    result = apply_deep_seek_config({})
    provider = result.get("models", {}).get("providers", {}).get("deepseek")

    assert provider == {
        "baseUrl": DEEPSEEK_BASE_URL,
        "api": "openai-completions",
        "models": [build_deep_seek_model_definition(model) for model in DEEPSEEK_MODEL_CATALOG],
    }
    assert resolve_agent_model_primary_value(result["agents"]["defaults"]["model"]) == (
        DEEPSEEK_DEFAULT_MODEL_REF
    )
    assert result["agents"]["defaults"]["models"][DEEPSEEK_DEFAULT_MODEL_REF] == {
        "alias": "DeepSeek",
    }


def test_advertises_max_thinking_levels_for_deep_seek_v4_models_only() -> None:
    captured = create_captured_plugin_registration(id="deepseek")
    deepseek_plugin.register(captured.api)
    provider = captured.providers[0]
    resolve_profile = provider["resolveThinkingProfile"]
    expected_v4_levels = ["off", "minimal", "low", "medium", "high", "xhigh", "max"]

    pro_profile = resolve_profile({"provider": "deepseek", "modelId": "deepseek-v4-pro"})
    assert [level["id"] for level in pro_profile["levels"]] == expected_v4_levels

    flash_profile = resolve_profile({"provider": "deepseek", "modelId": "deepseek-v4-flash"})
    assert flash_profile["defaultLevel"] == "high"
    assert [level["id"] for level in flash_profile["levels"]] == expected_v4_levels
    assert resolve_profile({"provider": "deepseek", "modelId": "deepseek-chat"}) is None
    assert resolve_profile({"provider": "deepseek", "modelId": "deepseek-reasoner"}) is None
    assert resolve_deep_seek_v4_thinking_profile("deepseek-chat") is None


def test_maps_thinking_levels_to_deep_seek_v4_payload_controls() -> None:
    model = {"provider": "deepseek", "id": "deepseek-v4-pro", "api": "openai-completions"}

    off_payload = _capture_payload(
        thinking_level="off",
        model=model,
        initial_payload={"model": "deepseek-v4-pro", "reasoning_effort": "high"},
    )
    assert off_payload["thinking"] == {"type": "disabled"}
    assert "reasoning_effort" not in off_payload

    xhigh_payload = _capture_payload(
        thinking_level="xhigh",
        model=model,
        initial_payload={"model": "deepseek-v4-pro", "reasoning_effort": "high"},
    )
    assert xhigh_payload["thinking"] == {"type": "enabled"}
    assert xhigh_payload["reasoning_effort"] == "max"


def test_preserves_replayed_reasoning_content_when_deep_seek_v4_thinking_is_enabled() -> None:
    captured: dict[str, Any] = {}
    model = _deep_seek_v4_model("deepseek-v4-flash")
    payload = {
        "messages": [
            {"role": "user", "content": "hi"},
            {
                "role": "assistant",
                "reasoning_content": "call reasoning",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {"name": "read", "arguments": "{}"},
                    }
                ],
            },
            {"role": "tool", "content": "ok"},
        ]
    }

    def base_stream_fn(_model: Any, _context: dict[str, Any], options: dict[str, Any] | None):
        if options and options.get("onPayload"):
            options["onPayload"](payload, _model)
        captured.update(payload)
        return {}

    wrapped = create_deep_seek_v4_thinking_wrapper(base_stream_fn, "high")
    assert wrapped is not None
    wrapped(model, {"messages": []}, {})

    assert captured["thinking"] == {"type": "enabled"}
    assert captured["reasoning_effort"] == "high"
    assistant_message = captured["messages"][1]
    assert assistant_message["role"] == "assistant"
    assert assistant_message["reasoning_content"] == "call reasoning"
    tool_call = assistant_message["tool_calls"][0]
    assert tool_call["id"] == "call_1"
    assert tool_call["type"] == "function"
    assert tool_call["function"]["name"] == "read"
    assert tool_call["function"]["arguments"] == "{}"


def test_adds_blank_reasoning_content_for_replayed_tool_calls_from_non_deep_seek_turns() -> None:
    model = _deep_seek_v4_model("deepseek-v4-pro")
    payload = {
        "messages": [
            {"role": "user", "content": "hi"},
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {"name": "read", "arguments": "{}"},
                    }
                ],
            },
            {"role": "tool", "content": "ok"},
        ]
    }
    captured = _capture_payload(thinking_level="high", model=model, initial_payload=payload)
    assistant_message = captured["messages"][1]
    assert assistant_message["role"] == "assistant"
    assert assistant_message["reasoning_content"] == ""
    tool_call = assistant_message["tool_calls"][0]
    assert tool_call["id"] == "call_1"
    assert tool_call["type"] == "function"
    assert tool_call["function"]["name"] == "read"
    assert tool_call["function"]["arguments"] == "{}"


def test_adds_blank_reasoning_content_for_replayed_plain_assistant_messages() -> None:
    model = _deep_seek_v4_model("deepseek-v4-pro")
    payload = {
        "messages": [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "Hello."},
            {"role": "user", "content": "next"},
        ]
    }
    captured = _capture_payload(thinking_level="high", model=model, initial_payload=payload)
    assistant_message = captured["messages"][1]
    assert assistant_message["role"] == "assistant"
    assert assistant_message["content"] == "Hello."
    assert assistant_message["reasoning_content"] == ""


def test_strips_replayed_reasoning_content_when_deep_seek_v4_thinking_is_disabled() -> None:
    model = _deep_seek_v4_model("deepseek-v4-flash")
    payload = {
        "messages": [
            {"role": "user", "content": "hi"},
            {
                "role": "assistant",
                "reasoning_content": "call reasoning",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {"name": "read", "arguments": "{}"},
                    }
                ],
            },
            {"role": "tool", "content": "ok"},
        ]
    }
    captured = _capture_payload(thinking_level="none", model=model, initial_payload=payload)
    assert captured["thinking"] == {"type": "disabled"}
    assert "reasoning_effort" not in captured
    assert "reasoning_content" not in captured["messages"][1]


def test_skips_thinking_wrapper_for_non_v4_models() -> None:
    captured: dict[str, Any] = {}

    def base_stream_fn(_model: Any, _context: dict[str, Any], options: dict[str, Any] | None):
        payload = {"model": "deepseek-chat"}
        if options and options.get("onPayload"):
            options["onPayload"](payload, _model)
        captured.update(payload)
        return {}

    wrapped = create_deep_seek_v4_thinking_wrapper(base_stream_fn, "high")
    assert wrapped is not None
    wrapped(
        {"provider": "deepseek", "id": "deepseek-chat", "api": "openai-completions"},
        {"messages": []},
        {},
    )
    assert captured == {"model": "deepseek-chat"}
    assert "thinking" not in captured
