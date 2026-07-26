"""Static Anthropic Vertex model catalog builder."""

from __future__ import annotations

from typing import Any

from openclaw.packages.normalization_core import normalize_lowercase_string_or_empty
from openclaw_extensions.anthropic_vertex.claude_contracts import (
    resolve_claude_fable5_model_identity,
)
from openclaw_extensions.anthropic_vertex.region import (
    GCP_VERTEX_CREDENTIALS_MARKER,
    resolve_anthropic_vertex_region,
)

ANTHROPIC_VERTEX_DEFAULT_MODEL_ID = "claude-sonnet-4-6"
ANTHROPIC_VERTEX_DEFAULT_CONTEXT_WINDOW = 1_000_000
ANTHROPIC_VERTEX_FABLE_MAX_TOKENS = 128_000


def _build_anthropic_vertex_model(params: dict[str, Any]) -> dict[str, Any]:
    model: dict[str, Any] = {
        "id": params["id"],
        "name": params["name"],
        "reasoning": params["reasoning"],
        "input": params["input"],
        "cost": params["cost"],
        "contextWindow": ANTHROPIC_VERTEX_DEFAULT_CONTEXT_WINDOW,
        "maxTokens": params["maxTokens"],
    }
    thinking_level_map = params.get("thinkingLevelMap")
    if thinking_level_map is not None:
        model["thinkingLevelMap"] = thinking_level_map
    return model


def _build_anthropic_vertex_catalog() -> list[dict[str, Any]]:
    return [
        _build_anthropic_vertex_model(
            {
                "id": "claude-fable-5",
                "name": "Claude Fable 5",
                "reasoning": True,
                "input": ["text", "image"],
                "cost": {"input": 10, "output": 50, "cacheRead": 1, "cacheWrite": 12.5},
                "maxTokens": ANTHROPIC_VERTEX_FABLE_MAX_TOKENS,
                "thinkingLevelMap": {
                    "off": "low",
                    "minimal": "low",
                    "xhigh": "xhigh",
                    "max": "max",
                },
            }
        ),
        _build_anthropic_vertex_model(
            {
                "id": "claude-opus-4-8",
                "name": "Claude Opus 4.8",
                "reasoning": True,
                "input": ["text", "image"],
                "cost": {"input": 5, "output": 25, "cacheRead": 0.5, "cacheWrite": 6.25},
                "maxTokens": 128000,
                "thinkingLevelMap": {"xhigh": "xhigh", "max": "max"},
            }
        ),
        _build_anthropic_vertex_model(
            {
                "id": "claude-opus-4-6",
                "name": "Claude Opus 4.6",
                "reasoning": True,
                "input": ["text", "image"],
                "cost": {"input": 5, "output": 25, "cacheRead": 0.5, "cacheWrite": 6.25},
                "maxTokens": 128000,
                "thinkingLevelMap": {"xhigh": None, "max": "max"},
            }
        ),
        _build_anthropic_vertex_model(
            {
                "id": ANTHROPIC_VERTEX_DEFAULT_MODEL_ID,
                "name": "Claude Sonnet 4.6",
                "reasoning": True,
                "input": ["text", "image"],
                "cost": {"input": 3, "output": 15, "cacheRead": 0.3, "cacheWrite": 3.75},
                "maxTokens": 128000,
                "thinkingLevelMap": {"xhigh": None, "max": "max"},
            }
        ),
    ]


def normalize_anthropic_vertex_resolved_model(
    model_id: str,
    model: dict[str, Any],
) -> dict[str, Any] | None:
    """Restore required Fable metadata after explicit catalog models replace the implicit row."""
    if not resolve_claude_fable5_model_identity({"id": model_id, "params": model.get("params")}):
        return None

    input_value = model.get("input")
    if not isinstance(input_value, list):
        input_value = []
    input_list = list(input_value)
    input = input_list if "image" in input_list else [*input_list, "image"]

    thinking_level_map = {
        "off": "low",
        "minimal": "low",
        "xhigh": "xhigh",
        "max": "max",
        **(model.get("thinkingLevelMap") if isinstance(model.get("thinkingLevelMap"), dict) else {}),
    }

    existing_map = model.get("thinkingLevelMap") if isinstance(model.get("thinkingLevelMap"), dict) else {}
    if (
        model.get("reasoning")
        and input == input_list
        and model.get("contextWindow") == ANTHROPIC_VERTEX_DEFAULT_CONTEXT_WINDOW
        and model.get("contextTokens") == ANTHROPIC_VERTEX_DEFAULT_CONTEXT_WINDOW
        and (model.get("maxTokens") or 0) >= ANTHROPIC_VERTEX_FABLE_MAX_TOKENS
        and existing_map.get("off") == "low"
        and existing_map.get("minimal") == "low"
        and existing_map.get("xhigh") == "xhigh"
        and existing_map.get("max") == "max"
    ):
        return None

    return {
        **model,
        "reasoning": True,
        "input": input,
        "contextWindow": ANTHROPIC_VERTEX_DEFAULT_CONTEXT_WINDOW,
        "contextTokens": ANTHROPIC_VERTEX_DEFAULT_CONTEXT_WINDOW,
        "maxTokens": max(model.get("maxTokens") or 0, ANTHROPIC_VERTEX_FABLE_MAX_TOKENS),
        "thinkingLevelMap": thinking_level_map,
    }


def build_anthropic_vertex_provider(
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the implicit Anthropic Vertex provider config for the current env."""
    env = params.get("env") if params else None
    region = resolve_anthropic_vertex_region(env)
    base_url = (
        "https://aiplatform.googleapis.com"
        if normalize_lowercase_string_or_empty(region) == "global"
        else f"https://{region}-aiplatform.googleapis.com"
    )
    return {
        "baseUrl": base_url,
        "api": "anthropic-messages",
        "apiKey": GCP_VERTEX_CREDENTIALS_MARKER,
        "models": _build_anthropic_vertex_catalog(),
    }


def read_configured_provider_catalog_entries(params: dict[str, Any]) -> list[dict[str, Any]]:
    """Read user-configured provider models as catalog entries for plugin discovery output."""
    config = params.get("config")
    provider_id = str(params["providerId"])
    published_provider_id = str(params.get("publishedProviderId") or provider_id)

    providers = config.get("models", {}).get("providers") if isinstance(config, dict) else None
    if not isinstance(providers, dict):
        return []

    provider_key = next(
        (key for key in providers if str(key).strip().lower() == provider_id.strip().lower()),
        None,
    )
    if provider_key is None:
        return []

    provider_config = providers.get(provider_key)
    if not isinstance(provider_config, dict):
        return []

    models = provider_config.get("models")
    if not isinstance(models, list):
        return []

    entries: list[dict[str, Any]] = []
    for model in models:
        if not isinstance(model, dict):
            continue
        raw_id = model.get("id")
        if not isinstance(raw_id, str) or not raw_id.strip():
            continue
        normalized_id = raw_id.strip()
        name = model.get("name")
        display_name = name.strip() if isinstance(name, str) and name.strip() else normalized_id
        entry: dict[str, Any] = {
            "provider": published_provider_id,
            "id": normalized_id,
            "name": display_name,
        }
        context_window = model.get("contextWindow")
        if isinstance(context_window, int) and context_window > 0:
            entry["contextWindow"] = context_window
        if isinstance(model.get("reasoning"), bool):
            entry["reasoning"] = model["reasoning"]
        raw_input = model.get("input")
        if isinstance(raw_input, list):
            normalized_input = [item for item in raw_input if item in ("text", "image", "audio", "video")]
            if normalized_input:
                entry["input"] = normalized_input
        entries.append(entry)
    return entries
