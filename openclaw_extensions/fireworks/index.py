"""Fireworks plugin entrypoint registers its OpenClaw integration."""

from __future__ import annotations

import re
from typing import Any

from openclaw.agents.defaults import DEFAULT_CONTEXT_TOKENS
from openclaw.plugin_sdk.plugin_entry import OpenClawPluginApi, define_plugin_entry
from openclaw.plugin_sdk.provider_auth_api_key import create_provider_api_key_auth_method
from openclaw_extensions.fireworks.model_id import is_fireworks_kimi_model_id
from openclaw_extensions.fireworks.onboard import (
    FIREWORKS_DEFAULT_MODEL_REF,
    apply_fireworks_config,
)
from openclaw_extensions.fireworks.provider_catalog import (
    FIREWORKS_BASE_URL,
    FIREWORKS_DEFAULT_CONTEXT_WINDOW,
    FIREWORKS_DEFAULT_MAX_TOKENS,
    FIREWORKS_DEFAULT_MODEL_ID,
    build_fireworks_provider,
    is_fireworks_catalog_model_id,
)
from openclaw_extensions.fireworks.stream import wrap_fireworks_provider_stream
from openclaw_extensions.fireworks.thinking_policy import resolve_fireworks_thinking_profile

PROVIDER_ID = "fireworks"
_GLM_MODEL_ID_PATTERN = re.compile(r"^glm[-_.]")


def _is_fireworks_glm_model_id(model_id: str) -> bool:
    normalized = model_id.strip().lower()
    last_segment = normalized.rsplit("/", 1)[-1]
    return _GLM_MODEL_ID_PATTERN.match(last_segment) is not None


def _resolve_fireworks_dynamic_input(model_id: str) -> list[str]:
    return ["text"] if _is_fireworks_glm_model_id(model_id) else ["text", "image"]


def _find_template_model(
    provider_id: str,
    template_id: str,
    ctx: dict[str, Any],
) -> dict[str, Any] | None:
    registry = ctx.get("modelRegistry")
    if registry is not None:
        find = registry.get("find") if isinstance(registry, dict) else getattr(registry, "find", None)
        if callable(find):
            return find(provider_id, template_id)
    models = ctx.get("models")
    if isinstance(models, list):
        for model in models:
            if not isinstance(model, dict):
                continue
            if model.get("provider") == provider_id and str(model.get("id", "")).lower() == template_id.lower():
                return model
    return None


def _clone_first_template_model(
    *,
    provider_id: str,
    model_id: str,
    template_ids: list[str],
    ctx: dict[str, Any],
    patch: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    trimmed_model_id = model_id.strip()
    seen: set[str] = set()
    for template_id in template_ids:
        if not template_id or template_id in seen:
            continue
        seen.add(template_id)
        template = _find_template_model(provider_id, template_id, ctx)
        if template is None:
            continue
        merged = {**template, "id": trimmed_model_id, "name": trimmed_model_id, **(patch or {})}
        return merged
    return None


def resolve_fireworks_dynamic_model(ctx: dict[str, Any]) -> dict[str, Any] | None:
    model_id = str(ctx.get("modelId", "")).strip()
    if not model_id:
        return None
    if is_fireworks_catalog_model_id(model_id):
        return None

    is_kimi_model = is_fireworks_kimi_model_id(model_id)
    input_modes = _resolve_fireworks_dynamic_input(model_id)
    cloned = _clone_first_template_model(
        provider_id=PROVIDER_ID,
        model_id=model_id,
        template_ids=[FIREWORKS_DEFAULT_MODEL_ID],
        ctx=ctx,
        patch={
            "provider": PROVIDER_ID,
            "reasoning": not is_kimi_model,
            "input": input_modes,
        },
    )
    if cloned is not None:
        return cloned

    return {
        "id": model_id,
        "name": model_id,
        "provider": PROVIDER_ID,
        "api": "openai-completions",
        "baseUrl": FIREWORKS_BASE_URL,
        "reasoning": not is_kimi_model,
        "input": input_modes,
        "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
        "contextWindow": FIREWORKS_DEFAULT_CONTEXT_WINDOW,
        "maxTokens": FIREWORKS_DEFAULT_MAX_TOKENS or DEFAULT_CONTEXT_TOKENS,
    }


def _register(api: OpenClawPluginApi) -> None:
    api.register_provider(
        {
            "id": PROVIDER_ID,
            "label": "Fireworks",
            "aliases": ["fireworks-ai"],
            "docsPath": "/providers/fireworks",
            "envVars": ["FIREWORKS_API_KEY"],
            "auth": [
                create_provider_api_key_auth_method(
                    {
                        "providerId": PROVIDER_ID,
                        "methodId": "api-key",
                        "label": "Fireworks API key",
                        "hint": "API key",
                        "optionKey": "fireworksApiKey",
                        "flagName": "--fireworks-api-key",
                        "envVar": "FIREWORKS_API_KEY",
                        "promptMessage": "Enter Fireworks API key",
                        "defaultModel": FIREWORKS_DEFAULT_MODEL_REF,
                        "wizard": {
                            "choiceId": "fireworks-api-key",
                            "choiceLabel": "Fireworks API key",
                            "choiceHint": "API key",
                            "groupId": "fireworks",
                            "groupLabel": "Fireworks",
                            "groupHint": "API key",
                        },
                    }
                ),
            ],
            "catalog": {
                "buildProvider": build_fireworks_provider,
                "allowExplicitBaseUrl": True,
            },
            "wrapStreamFn": wrap_fireworks_provider_stream,
            "resolveThinkingProfile": lambda ctx: resolve_fireworks_thinking_profile(
                str(ctx.get("modelId", ""))
            ),
            "resolveDynamicModel": resolve_fireworks_dynamic_model,
            "isModernModelRef": lambda _ctx=True: True,
            "applyConfig": apply_fireworks_config,
        }
    )


default = define_plugin_entry(
    id=PROVIDER_ID,
    name="Fireworks Provider",
    description="Bundled Fireworks AI provider plugin",
    register=_register,
)
