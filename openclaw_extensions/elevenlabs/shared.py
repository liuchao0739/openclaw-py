"""Elevenlabs plugin module implements shared behavior."""

from __future__ import annotations

import re

DEFAULT_ELEVENLABS_BASE_URL = "https://api.elevenlabs.io"

_VOICE_ID_PATTERN = re.compile(r"^[a-zA-Z0-9]{10,40}$")
_TRAILING_SLASHES = re.compile(r"/+$")


def is_valid_elevenlabs_voice_id(voice_id: str) -> bool:
    return bool(_VOICE_ID_PATTERN.match(voice_id))


def normalize_elevenlabs_base_url(base_url: str | None = None) -> str:
    trimmed = base_url.strip() if isinstance(base_url, str) else ""
    if trimmed:
        return _TRAILING_SLASHES.sub("", trimmed)
    return DEFAULT_ELEVENLABS_BASE_URL
