"""Media generation package.

Mirrors src/media-generation/. Full runtime deferred (depends on media-generation-core).
Provides model ref parser shared with image-generation.
"""

from __future__ import annotations

from typing import Any


def parse_generation_model_ref(
    raw: str | None,
) -> dict[str, str] | None:
    """Parse a media-generation model reference into provider/model components.

    Accepts "provider/model" format. Returns None for missing or invalid input.
    """
    if not isinstance(raw, str):
        return None
    trimmed = raw.strip()
    if not trimmed:
        return None
    if "/" not in trimmed:
        return None
    parts = trimmed.split("/", 1)
    provider = parts[0].strip()
    model = parts[1].strip()
    if not provider or not model:
        return None
    return {"provider": provider, "model": model}
