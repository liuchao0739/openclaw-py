"""Core facade for shared media provider id normalization.

Mirrors src/media-understanding/provider-id.ts (barrel re-export from
media-understanding-common). Self-contained normalization.
"""

from __future__ import annotations

from typing import Any

# Known media understanding provider IDs.
_KNOWN_PROVIDERS = frozenset({
    "openai",
    "anthropic",
    "google",
    "gemini",
    "azure",
    "aws",
    "bedrock",
    "ollama",
    "local",
})


def normalize_media_provider_id(value: Any) -> str | None:
    """Normalize a media provider ID to lowercase, or None for invalid values."""
    if not isinstance(value, str):
        return None
    trimmed = value.strip().lower()
    return trimmed or None
