"""TTS auto mode helpers decide when speech should be generated automatically.

Mirrors src/tts/tts-auto-mode.ts.
"""

from __future__ import annotations

from typing import Any

TTS_AUTO_MODES = frozenset({"off", "always", "inbound", "tagged"})


def normalize_tts_auto_mode(value: Any) -> str | None:
    """Normalize an unknown value into a supported TTS auto mode."""
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    if not normalized:
        return None
    return normalized if normalized in TTS_AUTO_MODES else None
