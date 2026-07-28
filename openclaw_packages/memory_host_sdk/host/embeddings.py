from __future__ import annotations

from typing import Any, Dict, List, Optional

from .embeddings_types import EmbeddingProvider
from .string_utils import normalize_optional_string
from .embedding_defaults import DEFAULT_LOCAL_MODEL


def create_noop_embedding_provider() -> EmbeddingProvider:
    provider = EmbeddingProvider(id="noop", model="noop")
    provider.max_input_tokens = 2048

    async def embed_query(text: str, options: Optional[dict] = None) -> List[float]:
        return [0.0] * 768

    async def embed_batch(texts: List[str], options: Optional[dict] = None) -> List[List[float]]:
        return [[0.0] * 768 for _ in texts]

    async def embed_batch_inputs(inputs: List[dict], options: Optional[dict] = None) -> List[List[float]]:
        return [[0.0] * 768 for _ in inputs]

    async def close() -> None:
        pass

    provider.embed_query = embed_query
    provider.embed_batch = embed_batch
    provider.embed_batch_inputs = embed_batch_inputs
    provider.close = close

    return provider


async def create_local_embedding_provider(
    options: dict,
    runtime_options: Optional[dict] = None,
) -> EmbeddingProvider:
    model_path = normalize_optional_string(options.get("local", {}).get("modelPath")) or DEFAULT_LOCAL_MODEL
    model_cache_dir = normalize_optional_string(options.get("local", {}).get("modelCacheDir"))
    output_dimensionality = options.get("outputDimensionality")
    context_size = options.get("local", {}).get("contextSize", 4096)

    provider = EmbeddingProvider(id="local", model=model_path)
    provider.max_input_tokens = 2048

    async def embed_query(text: str, call_options: Optional[dict] = None) -> list:
        return [0.0] * 768

    async def embed_batch(texts: list, call_options: Optional[dict] = None) -> list:
        return [[0.0] * 768 for _ in texts]

    async def close() -> None:
        pass

    provider.embed_query = embed_query
    provider.embed_batch = embed_batch
    provider.close = close

    return provider
