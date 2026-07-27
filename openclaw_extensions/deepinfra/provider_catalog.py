from typing import Dict, Optional

from .provider_models import (
    DEEPINFRA_BASE_URL,
    build_deepinfra_model_definition,
    discover_deepinfra_models,
)


def build_static_deepinfra_provider() -> Dict[str, any]:
    from .provider_models import DEEPINFRA_MANIFEST_PROVIDER

    return {
        "baseUrl": DEEPINFRA_BASE_URL,
        "api": "openai-completions",
        "models": [
            build_deepinfra_model_definition(m)
            for m in DEEPINFRA_MANIFEST_PROVIDER.get("models", [])
        ],
    }


async def build_deepinfra_provider(options: Dict[str, any] = None) -> Dict[str, any]:
    options = options or {}
    models = await discover_deepinfra_models(options)
    return {
        "baseUrl": DEEPINFRA_BASE_URL,
        "api": "openai-completions",
        "models": models,
    }


async def build_deepinfra_api_key_catalog(ctx: Dict[str, any]) -> Dict[str, any]:
    provider = await build_deepinfra_provider({
        "hasApiKey": True,
        "env": ctx.get("env"),
        "agentDir": ctx.get("agentDir"),
    })
    return {"provider": provider}