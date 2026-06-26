"""TLS fingerprint normalization accepts common SHA-256 display formats and
stores lowercase hex for config comparisons.

Mirrors src/infra/tls/fingerprint.ts.
"""

from __future__ import annotations

import re

# Pattern to strip SHA-256 label/prefix.
_SHA256_PREFIX_RE = re.compile(r"^sha-?256\s*:?\s*", re.IGNORECASE)
# Pattern to keep only hex characters.
_NON_HEX_RE = re.compile(r"[^a-fA-F0-9]")


def normalize_fingerprint(input: str) -> str:
    """Normalize a TLS fingerprint to lowercase hex without labels or separators."""
    if not isinstance(input, str):
        return ""
    trimmed = input.strip()
    without_prefix = _SHA256_PREFIX_RE.sub("", trimmed)
    hex_only = _NON_HEX_RE.sub("", without_prefix)
    return hex_only.lower()
