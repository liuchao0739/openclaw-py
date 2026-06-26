"""Identifier redaction helpers replace sensitive identifiers with stable hashes.

Mirrors src/logging/redact-identifier.ts.
"""

from __future__ import annotations

import hashlib
import math
from typing import Any


def sha256_hex_prefix(value: str, length: int = 12) -> str:
    """Return a stable sha256 hex prefix for non-secret identifier correlation."""
    safe_len = 12
    if isinstance(length, (int, float)) and not isinstance(length, bool):
        if not (math.isnan(length) or math.isinf(length)):
            safe_len = max(1, int(length))
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:safe_len]


def redact_identifier(
    value: Any,
    opts: dict[str, Any] | None = None,
) -> str:
    """Redact an identifier to a stable hash label, or '-' for missing values."""
    if not isinstance(value, str):
        return "-"
    trimmed = value.strip()
    if not trimmed:
        return "-"
    length = (opts or {}).get("len", 12)
    return f"sha256:{sha256_hex_prefix(trimmed, length)}"
