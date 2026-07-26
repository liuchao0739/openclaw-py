"""Video payload size helpers for base64-expanded request bodies."""

from __future__ import annotations

from .defaults import DEFAULT_VIDEO_MAX_BASE64_BYTES


def estimate_base64_size(bytes_count: int) -> int:
    """Estimate base64 size for a byte count."""
    return -(-bytes_count // 3) * 4


def resolve_video_max_base64_bytes(max_bytes: int) -> int:
    """Resolve video base64 byte limit from raw byte limit and global cap."""
    expanded = estimate_base64_size(max_bytes)
    return min(expanded, DEFAULT_VIDEO_MAX_BASE64_BYTES)
