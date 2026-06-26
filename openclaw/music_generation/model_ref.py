"""Parses model references for music generation requests.

Mirrors src/music-generation/model-ref.ts.
"""

from __future__ import annotations

from typing import Any


def parse_music_generation_model_ref(
    raw: Any,
) -> dict[str, str] | None:
    """Parse a music generation model ref into provider and model ids.

    Music generation uses the same provider/model ref grammar as other media
    capabilities, but keeps this wrapper for a dedicated capability boundary.
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
