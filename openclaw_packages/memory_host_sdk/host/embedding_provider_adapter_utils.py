from __future__ import annotations

from typing import List, Optional

from .string_utils import normalize_lowercase_string_or_empty


def is_missing_embedding_api_key_error(err: object) -> bool:
    return isinstance(err, Exception) and "No API key found for provider" in str(err)


def sanitize_embedding_cache_headers(
    headers: dict,
    excluded_header_names: list,
) -> list:
    excluded = {normalize_lowercase_string_or_empty(name) for name in excluded_header_names}
    result = []
    for key, value in headers.items():
        if normalize_lowercase_string_or_empty(key) not in excluded:
            result.append((key, value))
    result.sort(key=lambda x: x[0].lower())
    return result


def map_batch_embeddings_by_index(by_custom_id: dict, count: int) -> list:
    embeddings = []
    for i in range(count):
        embeddings.append(by_custom_id.get(str(i), []))
    return embeddings
