"""Detects suspicious system-style tags in external content.

Mirrors src/security/system-tags.ts.
"""

from __future__ import annotations

import re

_BRACKETED_SYSTEM_TAG_RE = re.compile(
    r"\[\s*(System\s*Message|System|Assistant|Internal)\s*\]", re.IGNORECASE
)
_LINE_SYSTEM_PREFIX_RE = re.compile(r"^(\s*)System:(?=\s|$)", re.IGNORECASE | re.MULTILINE)


def sanitize_inbound_system_tags(input: str) -> str:
    """Neutralize user-controlled strings that spoof internal system markers."""
    result = _BRACKETED_SYSTEM_TAG_RE.sub(lambda m: f"({m.group(1)})", input)
    result = _LINE_SYSTEM_PREFIX_RE.sub(r"\1System (untrusted):", result)
    return result
