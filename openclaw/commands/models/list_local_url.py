"""Local URL classifier for model provider status/list output."""

from __future__ import annotations

from urllib.parse import urlparse


def is_local_base_url(base_url: str) -> bool:
    """Return True for loopback, wildcard, and mDNS local base URLs."""
    try:
        parsed = urlparse(base_url)
        host = (parsed.hostname or "").lower().strip("[]")
        return (
            host == "localhost"
            or host == "127.0.0.1"
            or host == "0.0.0.0"
            or host == "::"
            or host == "::1"
            or host.endswith(".local")
        )
    except Exception:
        return False
