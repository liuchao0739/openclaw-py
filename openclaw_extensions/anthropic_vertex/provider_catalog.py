from typing import Any, List, Mapping, Optional

from .region import resolve_anthropic_vertex_region

ANTHROPIC_VERTEX_DEFAULT_MODEL_ID = "claude-sonnet-4-6"
ANTHROPIC_VERTEX_DEFAULT_CONTEXT_WINDOW = 1_000_000
ANTHROPIC_VERTEX_FABLE_MAX_TOKENS = 128_000
GCP_VERTEX_CREDENTIALS_MARKER = "gcp-vertex-credentials"


def _normalize_lowercase_string_or_empty(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip().lower()


def build_anthropic_vertex_model(params: dict) -> dict:
    model: dict = {
        "id": params["id"],
        "name": params["name"],
        "reasoning": params["reasoning"],
        "input": params["input"],
        "cost": params["cost"],
        "contextWindow": ANTHROPIC_VERTEX_DEFAULT_CONTEXT_WINDOW,
        "maxTokens": params["maxTokens"],
    }
    if params.get("thinkingLevelMap"):
        model["thinkingLevelMap"] = params["thinkingLevelMap"]
    return model


def build_anthropic_vertex_catalog() -> List[dict]:
    return [
        build_anthropic_vertex_model({
            "id": "claude-fable-5",
            "name": "Claude Fable 5",
            "reasoning": True,
            "input": ["text", "image"],
            "cost": {"input": 10, "output": 50, "cacheRead": 1, "cacheWrite": 12.5},
            "maxTokens": ANTHROPIC_VERTEX_FABLE_MAX_TOKENS,
            "thinkingLevelMap": {"off": "low", "minimal": "low", "xhigh": "xhigh", "max": "max"},
        }),
        build_anthropic_vertex_model({
            "id": "claude-opus-4-8",
            "name": "Claude Opus 4.8",
            "reasoning": True,
            "input": ["text", "image"],
            "cost": {"input": 5, "output": 25, "cacheRead": 0.5, "cacheWrite": 6.25},
            "maxTokens": 128000,
            "thinkingLevelMap": {"xhigh": "xhigh", "max": "max"},
        }),
        build_anthropic_vertex_model({
            "id": "claude-opus-4-6",
            "name": "Claude Opus 4.6",
            "reasoning": True,
            "input": ["text", "image"],
            "cost": {"input": 5, "output": 25, "cacheRead": 0.5, "cacheWrite": 6.25},
            "maxTokens": 128000,
            "thinkingLevelMap": {"xhigh": None, "max": "max"},
        }),
        build_anthropic_vertex_model({
            "id": ANTHROPIC_VERTEX_DEFAULT_MODEL_ID,
            "name": "Claude Sonnet 4.6",
            "reasoning": True,
            "input": ["text", "image"],
            "cost": {"input": 3, "output": 15, "cacheRead": 0.3, "cacheWrite": 3.75},
            "maxTokens": 128000,
            "thinkingLevelMap": {"xhigh": None, "max": "max"},
        }),
    ]


def normalize_anthropic_vertex_resolved_model(model_id: str, model: dict) -> Optional[dict]:
    from openclaw.plugin_sdk.provider_model_shared import resolve_claude_fable5_model_identity

    if not resolve_claude_fable5_model_identity({"id": model_id, "params": model.get("params")}):
        return None
    current_input = model.get("input", [])
    input_modalities = current_input if "image" in current_input else [*current_input, "image"]
    thinking_level_map = {
        "off": "low",
        "minimal": "low",
        "xhigh": "xhigh",
        "max": "max",
        **(model.get("thinkingLevelMap") or {}),
    }
    existing_map = model.get("thinkingLevelMap") or {}
    if (
        model.get("reasoning")
        and input_modalities == current_input
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
        "input": input_modalities,
        "contextWindow": ANTHROPIC_VERTEX_DEFAULT_CONTEXT_WINDOW,
        "contextTokens": ANTHROPIC_VERTEX_DEFAULT_CONTEXT_WINDOW,
        "maxTokens": max(model.get("maxTokens") or 0, ANTHROPIC_VERTEX_FABLE_MAX_TOKENS),
        "thinkingLevelMap": thinking_level_map,
    }


def build_anthropic_vertex_provider(params: Optional[dict] = None) -> dict:
    params = params or {}
    env = params.get("env")
    region = resolve_anthropic_vertex_region(env)
    base_url = (
        "https://aiplatform.googleapis.com"
        if _normalize_lowercase_string_or_empty(region) == "global"
        else f"https://{region}-aiplatform.googleapis.com"
    )
    return {
        "baseUrl": base_url,
        "api": "anthropic-messages",
        "apiKey": GCP_VERTEX_CREDENTIALS_MARKER,
        "models": build_anthropic_vertex_catalog(),
    }
