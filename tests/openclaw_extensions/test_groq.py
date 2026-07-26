"""Tests for the Groq provider extension."""

from __future__ import annotations

import inspect

from openclaw.plugin_sdk.plugin_test_runtime import create_captured_plugin_registration
from openclaw_extensions.groq import index
from openclaw_extensions.groq.api import resolve_groq_reasoning_compat_patch


def test_maps_groq_qwen3_reasoning_to_provider_native_none_default_values() -> None:
    assert resolve_groq_reasoning_compat_patch("qwen/qwen3-32b") == {
        "supportsReasoningEffort": True,
        "supportedReasoningEfforts": ["none", "default"],
        "reasoningEffortMap": {
            "adaptive": "default",
            "high": "default",
            "off": "none",
            "none": "none",
            "minimal": "default",
            "low": "default",
            "medium": "default",
            "max": "default",
            "xhigh": "default",
        },
    }


def test_keeps_gpt_oss_reasoning_on_groq_low_medium_high_contract() -> None:
    assert resolve_groq_reasoning_compat_patch("openai/gpt-oss-120b") == {
        "supportsReasoningEffort": True,
        "supportedReasoningEfforts": ["low", "medium", "high"],
    }


def test_registers_groq_model_and_media_providers() -> None:
    captured = create_captured_plugin_registration(id="groq")
    index.default.register(captured.api)

    assert len(captured.providers) == 1
    provider = captured.providers[0]
    assert provider == {
        "id": "groq",
        "label": "Groq",
        "docsPath": "/providers/groq",
        "envVars": ["GROQ_API_KEY"],
        "auth": provider["auth"],
    }
    assert len(provider["auth"]) == 1
    assert provider["auth"][0] == {
        "id": "api-key",
        "kind": "api_key",
        "label": "Groq API key",
        "hint": "Fast OpenAI-compatible inference",
        "wizard": {
            "choiceId": "groq-api-key",
            "choiceLabel": "Groq API key",
            "choiceHint": "Fast OpenAI-compatible inference",
            "groupId": "groq",
            "groupLabel": "Groq",
            "groupHint": "Fast OpenAI-compatible inference",
        },
        "run": provider["auth"][0]["run"],
        "runNonInteractive": provider["auth"][0]["runNonInteractive"],
    }
    assert inspect.iscoroutinefunction(provider["auth"][0]["run"])
    assert inspect.iscoroutinefunction(provider["auth"][0]["runNonInteractive"])

    assert len(captured.media_understanding_providers) == 1
    media_provider = captured.media_understanding_providers[0]
    transcribe_audio = media_provider.pop("transcribeAudio")
    assert media_provider == {
        "autoPriority": {"audio": 20},
        "capabilities": ["audio"],
        "defaultModels": {"audio": "whisper-large-v3-turbo"},
        "id": "groq",
    }
    assert inspect.iscoroutinefunction(transcribe_audio)
