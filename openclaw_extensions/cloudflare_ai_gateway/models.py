"""Model ids, default model metadata, and URL construction for Cloudflare AI Gateway."""

from __future__ import annotations

from typing import Any, Literal

from openclaw.plugin_sdk.provider_catalog_shared import ModelDefinitionConfig

CLOUDFLARE_AI_GATEWAY_PROVIDER_ID = "cloudflare-ai-gateway"
CLOUDFLARE_AI_GATEWAY_DEFAULT_MODEL_ID = "claude-sonnet-4-6"
CLOUDFLARE_AI_GATEWAY_DEFAULT_MODEL_REF = (
    f"{CLOUDFLARE_AI_GATEWAY_PROVIDER_ID}/{CLOUDFLARE_AI_GATEWAY_DEFAULT_MODEL_ID}"
)

_CLOUDFLARE_AI_GATEWAY_DEFAULT_CONTEXT_WINDOW = 200_000
_CLOUDFLARE_AI_GATEWAY_DEFAULT_MAX_TOKENS = 64_000
_CLOUDFLARE_AI_GATEWAY_DEFAULT_COST = {
    "input": 3,
    "output": 15,
    "cacheRead": 0.3,
    "cacheWrite": 3.75,
}


def build_cloudflare_ai_gateway_model_definition(
    params: dict[str, Any] | None = None,
) -> ModelDefinitionConfig:
    params = params or {}
    model_id = params.get("id")
    normalized_id = model_id.strip() if isinstance(model_id, str) and model_id.strip() else (
        CLOUDFLARE_AI_GATEWAY_DEFAULT_MODEL_ID
    )
    input_modes = params.get("input")
    normalized_input: list[Literal["text", "image"]] = (
        input_modes if isinstance(input_modes, list) else ["text", "image"]
    )
    return {
        "id": normalized_id,
        "name": params.get("name") or "Claude Sonnet 4.6",
        "reasoning": params.get("reasoning") if "reasoning" in params else True,
        "input": normalized_input,
        "cost": _CLOUDFLARE_AI_GATEWAY_DEFAULT_COST,
        "contextWindow": _CLOUDFLARE_AI_GATEWAY_DEFAULT_CONTEXT_WINDOW,
        "maxTokens": _CLOUDFLARE_AI_GATEWAY_DEFAULT_MAX_TOKENS,
    }


def resolve_cloudflare_ai_gateway_base_url(params: dict[str, str]) -> str:
    account_id = params.get("accountId", "").strip()
    gateway_id = params.get("gatewayId", "").strip()
    if not account_id or not gateway_id:
        return ""
    return f"https://gateway.ai.cloudflare.com/v1/{account_id}/{gateway_id}/anthropic"
