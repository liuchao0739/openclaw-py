from typing import Dict, Any

from .embedding_provider import build_deepinfra_embedding_provider


def build_deepinfra_memory_embedding_provider(options: Dict[str, any] = None) -> Dict[str, any]:
    options = options or {}
    embed_provider = build_deepinfra_embedding_provider(options)

    return {
        **embed_provider,
        "id": "deepinfra",
        "label": "DeepInfra",
    }

__all__ = ["build_deepinfra_memory_embedding_provider"]