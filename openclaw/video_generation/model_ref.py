"""Video model ref helpers parse provider-qualified video generation model ids.

Mirrors src/video-generation/model-ref.ts.
"""

from __future__ import annotations

from typing import Any


def parse_video_generation_model_ref(
    raw: Any,
) -> dict[str, str] | None:
    """Parse a video generation model ref into provider and model ids."""
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
