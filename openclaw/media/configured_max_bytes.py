"""Configured media size helpers resolve maximum byte limits by media kind.

Mirrors src/media/configured-max-bytes.ts.
"""

from __future__ import annotations

from typing import Any, Literal

MediaKind = Literal["image", "audio", "video", "document"]

_MB = 1024 * 1024
_MAX_BYTES_BY_KIND: dict[MediaKind, int] = {
    "image": 6 * _MB,
    "audio": 16 * _MB,
    "video": 16 * _MB,
    "document": 100 * _MB,
}


def resolve_configured_media_max_bytes(cfg: dict[str, Any] | None) -> int | None:
    """Resolve the global generated-media byte cap from the user-facing MB config value."""
    if not cfg:
        return None
    agents = cfg.get("agents")
    if not isinstance(agents, dict):
        return None
    defaults = agents.get("defaults")
    if not isinstance(defaults, dict):
        return None
    configured = defaults.get("mediaMaxMb")
    if isinstance(configured, (int, float)) and configured > 0:
        return int(configured * _MB)
    return None


def resolve_generated_media_max_bytes(
    cfg: dict[str, Any] | None,
    kind: MediaKind,
) -> int:
    """Return the configured media cap, falling back to the per-kind default."""
    return resolve_configured_media_max_bytes(cfg) or _MAX_BYTES_BY_KIND[kind]
