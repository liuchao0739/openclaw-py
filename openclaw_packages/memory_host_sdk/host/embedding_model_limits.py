from __future__ import annotations

from typing import Optional

from .embeddings_types import EmbeddingProvider


DEFAULT_EMBEDDING_MAX_INPUT_TOKENS = 8192
DEFAULT_LOCAL_EMBEDDING_MAX_INPUT_TOKENS = 2048


def resolve_embedding_max_input_tokens(provider: EmbeddingProvider) -> int:
    if provider.max_input_tokens is not None:
        return provider.max_input_tokens

    if provider.id == "local":
        return DEFAULT_LOCAL_EMBEDDING_MAX_INPUT_TOKENS

    return DEFAULT_EMBEDDING_MAX_INPUT_TOKENS
