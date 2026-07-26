"""Codex provider catalog constants and model definition helpers."""

from __future__ import annotations

from typing import Any

CODEX_PROVIDER_ID = "codex"
CODEX_BASE_URL = "https://chatgpt.com/backend-api"
CODEX_APP_SERVER_AUTH_MARKER = "codex-app-server"

DEFAULT_CONTEXT_WINDOW = 272_000
DEFAULT_MAX_TOKENS = 128_000

FALLBACK_CODEX_MODELS: list[dict[str, Any]] = [
    {
        "id": "gpt-5.5",
        "model": "gpt-5.5",
        "displayName": "gpt-5.5",
        "description": "Latest frontier agentic coding model.",
        "isDefault": True,
        "inputModalities": ["text", "image"],
        "supportedReasoningEfforts": ["low", "medium", "high", "xhigh"],
    },
    {
        "id": "gpt-5.4-mini",
        "model": "gpt-5.4-mini",
        "displayName": "GPT-5.4-Mini",
        "description": "Smaller frontier agentic coding model.",
        "inputModalities": ["text", "image"],
        "supportedReasoningEfforts": ["low", "medium", "high", "xhigh"],
    },
]


def _should_default_to_reasoning_model(model_id: str) -> bool:
    lower = model_id.lower()
    return lower.startswith(("gpt-5", "o1", "o3", "o4"))


def build_codex_model_definition(model: dict[str, Any]) -> dict[str, Any]:
    """Convert a Codex app-server model record into OpenClaw provider model config."""
    model_id = (str(model.get("id") or "")).strip() or (str(model.get("model") or "")).strip()
    display_name = model.get("displayName")
    name = display_name.strip() if isinstance(display_name, str) and display_name.strip() else model_id
    supported_reasoning = model.get("supportedReasoningEfforts") or []
    input_modalities = model.get("inputModalities") or []
    return {
        "id": model_id,
        "name": name,
        "api": "openai-chatgpt-responses",
        "reasoning": len(supported_reasoning) > 0 or _should_default_to_reasoning_model(model_id),
        "input": ["text", "image"] if "image" in input_modalities else ["text"],
        "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
        "contextWindow": DEFAULT_CONTEXT_WINDOW,
        "maxTokens": DEFAULT_MAX_TOKENS,
        "compat": {
            "supportsReasoningEffort": len(supported_reasoning) > 0,
            "supportsUsageInStreaming": True,
        },
    }


def build_codex_provider_config(models: list[dict[str, Any]]) -> dict[str, Any]:
    """Build the synthetic Codex provider config for a model list."""
    return {
        "baseUrl": CODEX_BASE_URL,
        "apiKey": CODEX_APP_SERVER_AUTH_MARKER,
        "auth": "token",
        "api": "openai-chatgpt-responses",
        "models": [build_codex_model_definition(model) for model in models],
    }
