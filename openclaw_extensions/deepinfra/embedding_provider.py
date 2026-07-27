from typing import Dict, List, Optional, Any

from .media_models import DEEPINFRA_BASE_URL, DEEPINFRA_EMBED_FALLBACK_MODELS, normalize_deepinfra_base_url, normalize_deepinfra_model_ref
from .provider_models import DeepInfraSurfaceModel


DEEPINFRA_EMBED_MAX_INPUT_TOKENS = 8192


def build_deepinfra_embedding_provider(options: Dict[str, any] = None) -> Dict[str, any]:
    options = options or {}
    embed_models = options.get("embedModels", [])

    ids = [m.id for m in embed_models] if embed_models else list(DEEPINFRA_EMBED_FALLBACK_MODELS)
    default_model = ids[0] if ids else DEEPINFRA_EMBED_FALLBACK_MODELS[0]

    return {
        "id": "deepinfra",
        "label": "DeepInfra",
        "models": ids,
        "defaultModel": default_model,
        "resolveModel": lambda ctx: normalize_deepinfra_model_ref(
            ctx.get("model"), default_model
        ),
        "resolveBaseUrl": lambda ctx: normalize_deepinfra_base_url(
            ctx.get("providerConfig", {}).get("baseUrl"), DEEPINFRA_BASE_URL
        ),
        "maxInputTokens": DEEPINFRA_EMBED_MAX_INPUT_TOKENS,
        "envKey": "DEEPINFRA_API_KEY",
        "buildRequest": lambda ctx: {
            "model": ctx.get("model"),
            "input": ctx.get("input"),
        },
        "response": {
            "embedding": lambda response: response.get("data", [])[0].get("embedding") if response.get("data") else [],
            "usage": lambda response: response.get("usage", {}),
        },
        "apiErrorLabel": "DeepInfra embedding API error",
        "missingApiKeyError": "DeepInfra API key missing",
    }

__all__ = ["build_deepinfra_embedding_provider"]