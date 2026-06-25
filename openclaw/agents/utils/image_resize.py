"""Image resizing helpers.

Deferred until image processing libraries are integrated.
"""

from __future__ import annotations

from typing import Any


def get_image_dimensions(data: bytes, mime_type: str) -> tuple[int, int] | None:
    """Get image dimensions from raw bytes. Deferred implementation."""
    del data, mime_type
    return None


def resize_image(
    data: bytes,
    *,
    max_width: int | None = None,
    max_height: int | None = None,
    mime_type: str = "image/png",
) -> bytes:
    """Resize an image. Deferred implementation returns input unchanged."""
    del max_width, max_height, mime_type
    return data
