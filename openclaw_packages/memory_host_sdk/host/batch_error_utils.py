from __future__ import annotations

from typing import Any, List, Optional

EMBEDDING_BATCH_ENDPOINT = "/batch"


def extract_batch_error_message(error: object) -> str:
    if isinstance(error, Exception):
        return str(error)
    return str(error)


def format_unavailable_batch_error(provider_id: str, detail: Optional[str] = None) -> str:
    base = f"Batch embedding is unavailable for provider {provider_id}"
    if detail:
        base += f": {detail}"
    return base
