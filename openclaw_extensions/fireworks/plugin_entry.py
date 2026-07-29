import re
from typing import Any, Optional, List, TypedDict

from .model_id import is_fireworks_kimi_model_id
from .onboard import apply_fireworks_config, FIREWORKS_DEFAULT_MODEL_REF
from .provider_catalog import (
    build_fireworks_provider,
    FIREWORKS_BASE_URL,
    FIREWORKS_DEFAULT_CONTEXT_WINDOW,
    FIREWORKS_DEFAULT_MAX_TOKENS,
    FIREWORKS_DEFAULT_MODEL_ID,
    is_fireworks_catalog_model_id,
)
from .stream import wrap_fireworks_provider_stream
from .thinking_policy import resolve_fireworks_thinking_profile

PROVIDER_ID = "fireworks"

_GLM_MODEL_PATTERN = re.compile(r"^glm[-_.]")


def _is_fireworks_glm_model_id(model_id: str) -> bool:
    normalized = model_id.strip().lower()
    parts = normalized.split("/")
    last_segment = parts[-1] if parts else normalized
    return bool(_GLM_MODEL_PATTERN.match(last_segment))


def _resolve_fireworks_dynamic_input(model_id: str) -> List[str]:
    if _is_fireworks_glm_model_id(model_id):
        return ["text"]
    return ["text", "image"]


def _clone_first_template_model(
    provider_id: str,
    model_id: str,
    template_ids: List[str],
    ctx: Any,
    patch: dict,
) -> Optional[dict]:
    return None


def _normalize_model_compat(
    id: str,
    name: str,
    provider: str,
    api: str,
    baseUrl: str,
    reasoning: bool,
    input: List[str],
    cost: dict,
    contextWindow: int,
    maxTokens: int,
) -> dict:
    return {
        "id": id,
        "name": name,
        "provider": provider,
        "api": api,
        "baseUrl": baseUrl,
        "reasoning": reasoning,
        "input": input,
        "cost": cost,
        "contextWindow": contextWindow,
        "maxTokens": maxTokens,
    }


def _resolve_fireworks_dynamic_model(ctx: Any) -> Optional[dict]:
    model_id = ctx.get("modelId", "").strip() if isinstance(ctx, dict) else ""
    if not model_id:
        return None

    if is_fireworks_catalog_model_id(model_id):
        return None

    is_kimi_model = is_fireworks_kimi_model_id(model_id)
    input_modalities = _resolve_fireworks_dynamic_input(model_id)

    cloned = _clone_first_template_model(
        provider_id=PROVIDER_ID,
        model_id=model_id,
        template_ids=[FIREWORKS_DEFAULT_MODEL_ID],
        ctx=ctx,
        patch={
            "provider": PROVIDER_ID,
            "reasoning": not is_kimi_model,
            "input": input_modalities,
        },
    )
    if cloned is not None:
        return cloned

    return _normalize_model_compat(
        id=model_id,
        name=model_id,
        provider=PROVIDER_ID,
        api="openai-completions",
        baseUrl=FIREWORKS_BASE_URL,
        reasoning=not is_kimi_model,
        input=input_modalities,
        cost={"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
        contextWindow=FIREWORKS_DEFAULT_CONTEXT_WINDOW,
        maxTokens=FIREWORKS_DEFAULT_MAX_TOKENS,
    )


OPENAI_COMPATIBLE_REPLAY_HOOKS: dict = {
    "replayModelRequest": None,
    "replayStreamChunk": None,
    "replayComplete": None,
}


class PluginEntry(TypedDict, total=False):
    id: str
    name: str
    description: str
    provider: dict


plugin_entry: PluginEntry = {
    "id": PROVIDER_ID,
    "name": "Fireworks Provider",
    "description": "Bundled Fireworks AI provider plugin",
    "provider": {
        "label": "Fireworks",
        "aliases": ["fireworks-ai"],
        "docsPath": "/providers/fireworks",
        "auth": [
            {
                "methodId": "api-key",
                "label": "Fireworks API key",
                "hint": "API key",
                "optionKey": "fireworksApiKey",
                "flagName": "--fireworks-api-key",
                "envVar": "FIREWORKS_API_KEY",
                "promptMessage": "Enter Fireworks API key",
                "defaultModel": FIREWORKS_DEFAULT_MODEL_REF,
                "applyConfig": lambda cfg: apply_fireworks_config(cfg),
            },
        ],
        "catalog": {
            "buildProvider": build_fireworks_provider,
            "allowExplicitBaseUrl": True,
        },
        **OPENAI_COMPATIBLE_REPLAY_HOOKS,
        "wrapStreamFn": wrap_fireworks_provider_stream,
        "resolveThinkingProfile": lambda params: resolve_fireworks_thinking_profile(
            params.get("modelId", "")
        ),
        "resolveDynamicModel": lambda ctx: _resolve_fireworks_dynamic_model(ctx),
        "isModernModelRef": lambda: True,
    },
}
