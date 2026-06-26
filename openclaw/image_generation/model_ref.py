"""Parses image-generation model references into provider/model components.

Mirrors src/image-generation/model-ref.ts. Image model refs share the generic
media-generation provider/model grammar: "provider/model" when explicit,
otherwise null for default resolution.
"""

from __future__ import annotations

from typing import Any


def parse_image_generation_model_ref(
    raw: str | None,
) -> dict[str, str] | None:
    """Parse an image-generation model reference into provider/model components.

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
