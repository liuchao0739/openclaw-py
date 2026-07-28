from __future__ import annotations

from typing import Any

from openclaw.plugin_sdk.memory_core_host_engine_embeddings import (
    is_missing_embedding_api_key_error,
    MemoryEmbeddingProviderAdapter,
)
from openclaw_extensions.amazon_bedrock.embedding_provider import (
    create_bedrock_embedding_provider,
    DEFAULT_BEDROCK_EMBEDDING_MODEL,
    has_aws_credentials,
)

bedrock_memory_embedding_provider_adapter: MemoryEmbeddingProviderAdapter = {
    "id": "bedrock",
    "defaultModel": DEFAULT_BEDROCK_EMBEDDING_MODEL,
    "transport": "remote",
    "authProviderId": "amazon-bedrock",
    "autoSelectPriority": 60,
    "allowExplicitWhenConfiguredAuto": True,
    "shouldContinueAutoSelection": is_missing_embedding_api_key_error,
    "create": lambda options: _create_bedrock_embedding(options),
}


async def _create_bedrock_embedding(options: dict[str, Any]) -> dict[str, Any]:
    if not await has_aws_credentials():
        raise ValueError(
            'No API key found for provider "bedrock". '
            "AWS credentials are not available. "
            "Set AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY, AWS_PROFILE, or AWS_BEARER_TOKEN_BEDROCK, "
            "configure an EC2/ECS/EKS role, "
            "or set agents.defaults.memorySearch.provider to another provider.",
        )
    result = await create_bedrock_embedding_provider({
        **options,
        "provider": "bedrock",
        "fallback": "none",
    })
    provider = result["provider"]
    client = result["client"]
    return {
        "provider": provider,
        "runtime": {
            "id": "bedrock",
            "cacheKeyData": {
                "provider": "bedrock",
                "region": client["region"],
                "model": client["model"],
                "dimensions": client.get("dimensions"),
            },
        },
    }


__all__ = ["bedrock_memory_embedding_provider_adapter"]