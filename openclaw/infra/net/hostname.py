"""Hostname normalization helpers keep SSRF and proxy policy comparisons stable
across case, trailing dots, and bracketed IPv6 literals.

Mirrors src/infra/net/hostname.ts.
"""

from __future__ import annotations

import re


def normalize_hostname(hostname: str) -> str:
    """Normalize a hostname for policy comparisons."""
    if not isinstance(hostname, str):
        return ""
    normalized = hostname.strip().lower()
    normalized = re.sub(r"\.+$", "", normalized)
    if normalized.startswith("[") and normalized.endswith("]"):
        return normalized[1:-1]
    return normalized
