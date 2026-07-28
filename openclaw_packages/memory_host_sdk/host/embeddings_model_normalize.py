from __future__ import annotations

from typing import Optional


def normalize_embedding_model_with_prefixes(model: str) -> str:
    if not model:
        return model
    prefixes = ["text-embedding-", "embedding-"]
    for prefix in prefixes:
        if model.startswith(prefix):
            return model[len(prefix):]
    return model
