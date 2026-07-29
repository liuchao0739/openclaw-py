"""Bounded regex replacement prevents large support/log strings from monopolizing the event loop.

Mirrors src/logging/redact-bounded.ts.
"""

from __future__ import annotations

import re
from typing import Callable

_REDACT_REGEX_CHUNK_THRESHOLD = 32768
_REDACT_REGEX_CHUNK_SIZE = 16384


def replace_pattern_bounded(
    text: str,
    pattern: re.Pattern,
    replacer: Callable[..., str],
    options: dict[str, int] | None = None,
) -> str:
    chunk_threshold = (options or {}).get("chunkThreshold", _REDACT_REGEX_CHUNK_THRESHOLD)
    chunk_size = (options or {}).get("chunkSize", _REDACT_REGEX_CHUNK_SIZE)
    if chunk_threshold <= 0 or chunk_size <= 0 or len(text) <= chunk_threshold:
        return pattern.sub(replacer, text)
    output = ""
    for index in range(0, len(text), chunk_size):
        output += pattern.sub(replacer, text[index : index + chunk_size])
    return output


__all__ = ["replace_pattern_bounded"]
