from __future__ import annotations

from typing import Any, Dict, List, Optional

EMBEDDING_BATCH_ENDPOINT = "/batch"


def build_batch_headers(
    api_key: str,
    extra_headers: Optional[dict] = None,
) -> dict:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if extra_headers:
        headers.update(extra_headers)
    return headers


def normalize_batch_base_url(base_url: str) -> str:
    if not base_url:
        return ""
    return base_url.rstrip("/")
