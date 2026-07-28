from __future__ import annotations

from typing import List, Optional

from .embedding_input_limits import estimate_utf8_bytes, split_text_to_utf8_byte_limit
from .embedding_inputs import has_non_text_embedding_parts
from .embedding_model_limits import resolve_embedding_max_input_tokens
from .embeddings_types import EmbeddingProvider
from .hash import hash_text


def enforce_embedding_max_input_tokens(
    provider: EmbeddingProvider,
    chunks: list,
    hard_max_input_tokens: Optional[int] = None,
) -> list:
    provider_max = resolve_embedding_max_input_tokens(provider)
    if hard_max_input_tokens is not None and hard_max_input_tokens > 0:
        max_input_tokens = min(provider_max, hard_max_input_tokens)
    else:
        max_input_tokens = provider_max

    result = []
    for chunk in chunks:
        if has_non_text_embedding_parts(chunk.get("embeddingInput")):
            result.append(chunk)
            continue
        if estimate_utf8_bytes(chunk.get("text", "")) <= max_input_tokens:
            result.append(chunk)
            continue

        for text_part in split_text_to_utf8_byte_limit(chunk.get("text", ""), max_input_tokens):
            result.append({
                "start_line": chunk["start_line"],
                "end_line": chunk["end_line"],
                "text": text_part,
                "hash": hash_text(text_part),
                "embedding_input": {"text": text_part},
            })

    return result
