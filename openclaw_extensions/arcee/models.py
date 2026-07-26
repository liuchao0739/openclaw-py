"""Arcee model catalog metadata for direct and OpenRouter-routed providers."""

from __future__ import annotations

from typing import Any

from openclaw.plugin_sdk.provider_catalog_shared import ModelDefinitionConfig

ARCEE_BASE_URL = "https://api.arcee.ai/api/v1"

ARCEE_MODEL_CATALOG: list[dict[str, Any]] = [
    {
        "id": "trinity-mini",
        "name": "Trinity Mini 26B",
        "reasoning": False,
        "input": ["text"],
        "contextWindow": 131072,
        "maxTokens": 80000,
        "cost": {
            "input": 0.045,
            "output": 0.15,
            "cacheRead": 0.045,
            "cacheWrite": 0.045,
        },
    },
    {
        "id": "trinity-large-preview",
        "name": "Trinity Large Preview",
        "reasoning": False,
        "input": ["text"],
        "contextWindow": 131072,
        "maxTokens": 16384,
        "cost": {
            "input": 0.25,
            "output": 1,
            "cacheRead": 0.25,
            "cacheWrite": 0.25,
        },
    },
    {
        "id": "trinity-large-thinking",
        "name": "Trinity Large Thinking",
        "reasoning": True,
        "input": ["text"],
        "contextWindow": 262144,
        "maxTokens": 80000,
        "cost": {
            "input": 0.25,
            "output": 0.9,
            "cacheRead": 0.25,
            "cacheWrite": 0.25,
        },
        "compat": {
            "supportsTools": False,
            "supportsReasoningEffort": False,
        },
    },
]


def build_arcee_model_definition(model: dict[str, Any]) -> ModelDefinitionConfig:
    result: ModelDefinitionConfig = {
        "id": model["id"],
        "name": model["name"],
        "api": "openai-completions",
        "reasoning": model["reasoning"],
        "input": model["input"],
        "cost": model["cost"],
        "contextWindow": model["contextWindow"],
        "maxTokens": model["maxTokens"],
    }
    compat = model.get("compat")
    if compat:
        result["compat"] = compat
    return result
