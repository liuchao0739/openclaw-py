"""Tests for the Fireworks provider extension."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from openclaw.plugin_sdk.plugin_test_runtime import create_captured_plugin_registration
from openclaw_extensions.fireworks.index import default as fireworks_plugin
from openclaw_extensions.fireworks.index import resolve_fireworks_dynamic_model
from openclaw_extensions.fireworks.provider_catalog import (
    FIREWORKS_BASE_URL,
    FIREWORKS_DEFAULT_CONTEXT_WINDOW,
    FIREWORKS_DEFAULT_MAX_TOKENS,
    FIREWORKS_DEFAULT_MODEL_ID,
    build_fireworks_provider,
)
from openclaw_extensions.fireworks.provider_policy_api import resolve_thinking_profile
from openclaw_extensions.fireworks.stream import (
    create_fireworks_kimi_thinking_disabled_wrapper,
    wrap_fireworks_provider_stream,
)

FIREWORKS_KIMI_K2_6_MODEL_ID = "accounts/fireworks/models/kimi-k2p6"

_MANIFEST_PATH = (
    Path(__file__).resolve().parents[2]
    / "openclaw_extensions"
    / "fireworks"
    / "openclaw.plugin.json"
)


def _read_manifest() -> dict[str, Any]:
    return json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))


def _create_fireworks_default_runtime_model(*, reasoning: bool) -> dict[str, Any]:
    return {
        "id": FIREWORKS_DEFAULT_MODEL_ID,
        "name": FIREWORKS_DEFAULT_MODEL_ID,
        "provider": "fireworks",
        "api": "openai-completions",
        "baseUrl": FIREWORKS_BASE_URL,
        "reasoning": reasoning,
        "input": ["text", "image"],
        "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
        "contextWindow": FIREWORKS_DEFAULT_CONTEXT_WINDOW,
        "maxTokens": FIREWORKS_DEFAULT_MAX_TOKENS,
    }


def _create_provider_dynamic_model_context(
    *,
    provider: str,
    model_id: str,
    models: list[dict[str, Any]],
) -> dict[str, Any]:
    def find(provider_id: str, lookup_model_id: str) -> dict[str, Any] | None:
        for model in models:
            if (
                model.get("provider") == provider_id
                and str(model.get("id", "")).lower() == lookup_model_id.lower()
            ):
                return model
        return None

    return {
        "provider": provider,
        "modelId": model_id,
        "modelRegistry": {"find": find},
    }


def test_registers_fireworks_with_api_key_auth_wizard_metadata() -> None:
    captured = create_captured_plugin_registration(id="fireworks")
    fireworks_plugin.register(captured.api)
    assert captured.providers, "expected Fireworks provider registration"
    provider = captured.providers[0]

    assert provider["id"] == "fireworks"
    assert provider["label"] == "Fireworks"
    assert provider["aliases"] == ["fireworks-ai"]
    assert provider["envVars"] == ["FIREWORKS_API_KEY"]
    assert len(provider["auth"]) == 1
    assert provider["auth"][0]["id"] == "api-key"
    assert provider["auth"][0]["wizard"]["choiceId"] == "fireworks-api-key"

    manifest = _read_manifest()
    assert manifest["providerAuthChoices"][0]["choiceId"] == "fireworks-api-key"


def test_builds_the_fireworks_catalog() -> None:
    catalog_provider = build_fireworks_provider()

    assert catalog_provider["api"] == "openai-completions"
    assert catalog_provider["baseUrl"] == FIREWORKS_BASE_URL
    models = catalog_provider.get("models")
    assert models is not None
    assert [model["id"] for model in models] == [
        FIREWORKS_KIMI_K2_6_MODEL_ID,
        FIREWORKS_DEFAULT_MODEL_ID,
    ]
    assert models[0]["reasoning"] is False
    assert models[0]["input"] == ["text", "image"]
    assert models[0]["contextWindow"] == 262144
    assert models[0]["maxTokens"] == 262144
    assert models[1]["reasoning"] is False
    assert models[1]["input"] == ["text", "image"]
    assert models[1]["contextWindow"] == FIREWORKS_DEFAULT_CONTEXT_WINDOW
    assert models[1]["maxTokens"] == FIREWORKS_DEFAULT_MAX_TOKENS


def test_resolves_forward_compat_fireworks_model_ids_from_default_template() -> None:
    resolved = resolve_fireworks_dynamic_model(
        _create_provider_dynamic_model_context(
            provider="fireworks",
            model_id="accounts/fireworks/models/qwen3.6-plus",
            models=[_create_fireworks_default_runtime_model(reasoning=True)],
        )
    )

    assert resolved is not None
    assert resolved["provider"] == "fireworks"
    assert resolved["id"] == "accounts/fireworks/models/qwen3.6-plus"
    assert resolved["api"] == "openai-completions"
    assert resolved["baseUrl"] == FIREWORKS_BASE_URL
    assert resolved["reasoning"] is True
    assert resolved["input"] == ["text", "image"]


def test_disables_reasoning_metadata_for_fireworks_kimi_dynamic_models() -> None:
    resolved = resolve_fireworks_dynamic_model(
        _create_provider_dynamic_model_context(
            provider="fireworks",
            model_id="accounts/fireworks/models/kimi-k2p5",
            models=[_create_fireworks_default_runtime_model(reasoning=False)],
        )
    )

    assert resolved is not None
    assert resolved["provider"] == "fireworks"
    assert resolved["id"] == "accounts/fireworks/models/kimi-k2p5"
    assert resolved["reasoning"] is False
    assert resolved["input"] == ["text", "image"]


def test_keeps_fireworks_glm_dynamic_models_text_only() -> None:
    resolved = resolve_fireworks_dynamic_model(
        _create_provider_dynamic_model_context(
            provider="fireworks",
            model_id="accounts/fireworks/models/glm-5p1",
            models=[_create_fireworks_default_runtime_model(reasoning=False)],
        )
    )

    assert resolved is not None
    assert resolved["provider"] == "fireworks"
    assert resolved["id"] == "accounts/fireworks/models/glm-5p1"
    assert resolved["input"] == ["text"]


def test_disables_reasoning_metadata_for_fireworks_kimi_k25_aliases() -> None:
    resolved = resolve_fireworks_dynamic_model(
        _create_provider_dynamic_model_context(
            provider="fireworks",
            model_id="accounts/fireworks/routers/kimi-k2.5-turbo",
            models=[_create_fireworks_default_runtime_model(reasoning=False)],
        )
    )

    assert resolved is not None
    assert resolved["provider"] == "fireworks"
    assert resolved["id"] == "accounts/fireworks/routers/kimi-k2.5-turbo"
    assert resolved["reasoning"] is False


def test_defers_manifest_catalog_models_to_core_static_catalog_resolution() -> None:
    for model_id in [FIREWORKS_KIMI_K2_6_MODEL_ID, FIREWORKS_DEFAULT_MODEL_ID]:
        resolved = resolve_fireworks_dynamic_model(
            _create_provider_dynamic_model_context(
                provider="fireworks",
                model_id=model_id,
                models=[_create_fireworks_default_runtime_model(reasoning=False)],
            )
        )
        assert resolved is None


def test_exposes_off_only_thinking_policy_for_fireworks_kimi_models() -> None:
    captured = create_captured_plugin_registration(id="fireworks")
    fireworks_plugin.register(captured.api)
    provider = captured.providers[0]
    resolve_profile = provider["resolveThinkingProfile"]

    assert resolve_profile(
        {"provider": "fireworks", "modelId": "accounts/fireworks/routers/kimi-k2p5-turbo"}
    ) == {
        "levels": [{"id": "off"}],
        "defaultLevel": "off",
    }
    assert resolve_profile({"provider": "fireworks", "modelId": FIREWORKS_KIMI_K2_6_MODEL_ID}) == {
        "levels": [{"id": "off"}],
        "defaultLevel": "off",
    }
    assert (
        resolve_profile(
            {"provider": "fireworks", "modelId": "accounts/fireworks/models/qwen3.6-plus"}
        )
        is None
    )
    assert resolve_thinking_profile({"modelId": FIREWORKS_KIMI_K2_6_MODEL_ID}) == {
        "levels": [{"id": "off"}],
        "defaultLevel": "off",
    }
    assert resolve_thinking_profile({"modelId": "accounts/fireworks/models/qwen3.6-plus"}) is None


def _capture_payload(
    *,
    provider: str,
    api: str,
    model_id: str,
    initial_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    captured: dict[str, Any] = {}

    def base_stream_fn(_model: Any, _context: dict[str, Any], options: dict[str, Any] | None):
        payload = dict(initial_payload or {})
        if options and options.get("onPayload"):
            options["onPayload"](payload, _model)
        captured.update(payload)
        return {}

    wrapped = create_fireworks_kimi_thinking_disabled_wrapper(base_stream_fn)
    wrapped(
        {"api": api, "provider": provider, "id": model_id},
        {"messages": []},
        {},
    )
    return captured


def test_forces_thinking_disabled_for_fireworks_kimi_models() -> None:
    assert _capture_payload(
        provider="fireworks",
        api="openai-completions",
        model_id="accounts/fireworks/routers/kimi-k2p5-turbo",
    ) == {"thinking": {"type": "disabled"}}


def test_forces_thinking_disabled_for_fireworks_kimi_k25_aliases() -> None:
    assert _capture_payload(
        provider="fireworks",
        api="openai-completions",
        model_id="accounts/fireworks/routers/kimi-k2.5-turbo",
    ) == {"thinking": {"type": "disabled"}}


def test_forces_thinking_disabled_for_fireworks_kimi_k26_models() -> None:
    assert _capture_payload(
        provider="fireworks",
        api="openai-completions",
        model_id="accounts/fireworks/models/kimi-k2p6",
    ) == {"thinking": {"type": "disabled"}}
    assert _capture_payload(
        provider="fireworks",
        api="openai-completions",
        model_id="accounts/fireworks/routers/kimi-k2.6-turbo",
    ) == {"thinking": {"type": "disabled"}}


def test_strips_reasoning_fields_when_disabling_fireworks_kimi_thinking() -> None:
    k2p5_payload = _capture_payload(
        provider="fireworks",
        api="openai-completions",
        model_id="accounts/fireworks/models/kimi-k2p5",
        initial_payload={
            "reasoning_effort": "low",
            "reasoning": {"effort": "low"},
            "reasoningEffort": "low",
        },
    )
    k2p6_payload = _capture_payload(
        provider="fireworks",
        api="openai-completions",
        model_id="accounts/fireworks/models/kimi-k2p6",
        initial_payload={
            "reasoning_effort": "low",
            "reasoning": {"effort": "low"},
            "reasoningEffort": "low",
        },
    )

    assert k2p5_payload == {"thinking": {"type": "disabled"}}
    assert k2p6_payload == {"thinking": {"type": "disabled"}}


def test_passes_sanitized_payloads_to_caller_on_payload_hooks() -> None:
    callback_payload: dict[str, Any] = {}

    def base_stream_fn(_model: Any, _context: dict[str, Any], options: dict[str, Any] | None):
        payload = {
            "reasoning_effort": "high",
            "reasoning": {"effort": "high"},
        }
        if options and options.get("onPayload"):
            options["onPayload"](payload, _model)
        return {}

    wrapped = create_fireworks_kimi_thinking_disabled_wrapper(base_stream_fn)
    wrapped(
        {
            "api": "openai-completions",
            "provider": "fireworks",
            "id": "accounts/fireworks/routers/kimi-k2p5-turbo",
        },
        {"messages": []},
        {
            "onPayload": lambda payload, _model: callback_payload.update(payload),
        },
    )

    assert callback_payload == {"thinking": {"type": "disabled"}}


def test_returns_no_provider_wrapper_for_non_target_fireworks_requests() -> None:
    assert (
        wrap_fireworks_provider_stream(
            {
                "provider": "fireworks",
                "modelId": "accounts/fireworks/models/qwen3.6-plus",
                "model": {
                    "api": "openai-completions",
                    "provider": "fireworks",
                    "id": "accounts/fireworks/models/qwen3.6-plus",
                },
                "streamFn": None,
            }
        )
        is None
    )

    assert (
        wrap_fireworks_provider_stream(
            {
                "provider": "fireworks",
                "modelId": "accounts/fireworks/routers/kimi-k2p5-turbo",
                "model": {
                    "api": "openai-responses",
                    "provider": "fireworks",
                    "id": "accounts/fireworks/routers/kimi-k2p5-turbo",
                },
                "streamFn": None,
            }
        )
        is None
    )

    assert callable(
        wrap_fireworks_provider_stream(
            {
                "provider": "fireworks-ai",
                "modelId": "accounts/fireworks/routers/kimi-k2p5-turbo",
                "model": {
                    "api": "openai-completions",
                    "provider": "fireworks-ai",
                    "id": "accounts/fireworks/routers/kimi-k2p5-turbo",
                },
                "streamFn": None,
            }
        )
    )

    assert (
        wrap_fireworks_provider_stream(
            {
                "provider": "openai",
                "modelId": "gpt-5.4",
                "model": {
                    "api": "openai-completions",
                    "provider": "openai",
                    "id": "gpt-5.4",
                },
                "streamFn": None,
            }
        )
        is None
    )
