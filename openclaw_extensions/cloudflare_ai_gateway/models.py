from typing import List, Optional, TypedDict


class ModelCost(TypedDict, total=False):
    input: float
    output: float
    cacheRead: float
    cacheWrite: float


class ModelDefinitionConfig(TypedDict, total=False):
    id: str
    name: str
    reasoning: bool
    input: List[str]
    cost: ModelCost
    contextWindow: int
    maxTokens: int


CLOUDFLARE_AI_GATEWAY_PROVIDER_ID = "cloudflare-ai-gateway"
CLOUDFLARE_AI_GATEWAY_DEFAULT_MODEL_ID = "claude-sonnet-4-6"
CLOUDFLARE_AI_GATEWAY_DEFAULT_MODEL_REF = f"{CLOUDFLARE_AI_GATEWAY_PROVIDER_ID}/{CLOUDFLARE_AI_GATEWAY_DEFAULT_MODEL_ID}"

_CLOUDFLARE_AI_GATEWAY_DEFAULT_CONTEXT_WINDOW = 200_000
_CLOUDFLARE_AI_GATEWAY_DEFAULT_MAX_TOKENS = 64_000
_CLOUDFLARE_AI_GATEWAY_DEFAULT_COST: ModelCost = {
    "input": 3,
    "output": 15,
    "cacheRead": 0.3,
    "cacheWrite": 3.75,
}


def build_cloudflare_ai_gateway_model_definition(
    params: Optional[dict] = None,
) -> ModelDefinitionConfig:
    params = params or {}
    raw_id = params.get("id", "")
    model_id = raw_id.strip() if isinstance(raw_id, str) else raw_id
    if not model_id:
        model_id = CLOUDFLARE_AI_GATEWAY_DEFAULT_MODEL_ID
    return {
        "id": model_id,
        "name": params.get("name", "Claude Sonnet 4.6"),
        "reasoning": params.get("reasoning", True),
        "input": params.get("input", ["text", "image"]),
        "cost": _CLOUDFLARE_AI_GATEWAY_DEFAULT_COST,
        "contextWindow": _CLOUDFLARE_AI_GATEWAY_DEFAULT_CONTEXT_WINDOW,
        "maxTokens": _CLOUDFLARE_AI_GATEWAY_DEFAULT_MAX_TOKENS,
    }


def resolve_cloudflare_ai_gateway_base_url(params: dict) -> str:
    account_id = params["accountId"].strip()
    gateway_id = params["gatewayId"].strip()
    if not account_id or not gateway_id:
        return ""
    return f"https://gateway.ai.cloudflare.com/v1/{account_id}/{gateway_id}/anthropic"
