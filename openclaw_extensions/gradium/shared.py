"""Gradium plugin shared constants and URL normalization."""

from __future__ import annotations

DEFAULT_GRADIUM_BASE_URL = "https://api.gradium.ai"
DEFAULT_GRADIUM_VOICE_ID = "YTpq7expH9539ERJ"

GRADIUM_VOICES: list[dict[str, str]] = [
    {"id": "YTpq7expH9539ERJ", "name": "Emma"},
    {"id": "LFZvm12tW_z0xfGo", "name": "Kent"},
    {"id": "Eu9iL_CYe8N-Gkx_", "name": "Tiffany"},
    {"id": "2H4HY2CBNyJHBCrP", "name": "Christina"},
    {"id": "jtEKaLYNn6iif5PR", "name": "Sydney"},
    {"id": "KWJiFWu2O9nMPYcR", "name": "John"},
    {"id": "3jUdJyOi9pgbxBTK", "name": "Arthur"},
]


def normalize_gradium_base_url(base_url: str | None = None) -> str:
    trimmed = base_url.strip() if isinstance(base_url, str) else None
    if trimmed:
        return trimmed.rstrip("/")
    return DEFAULT_GRADIUM_BASE_URL
