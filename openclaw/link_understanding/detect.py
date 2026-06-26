"""Link detection extracts unique safe bare HTTP(S) URLs from inbound text while
filtering SSRF targets.

Mirrors src/link-understanding/detect.ts. Self-contained port with basic SSRF
hostname filtering (localhost/private IPs).
"""

from __future__ import annotations

import ipaddress
import re
from typing import Any
from urllib.parse import urlparse

from .defaults import DEFAULT_MAX_LINKS

_MARKDOWN_LINK_RE = re.compile(r"\[[^\]]*]\((https?://\S+?)\)", re.IGNORECASE)
_BARE_LINK_RE = re.compile(r"https?://\S+", re.IGNORECASE)

_BLOCKED_HOSTNAMES = frozenset({"localhost", "0.0.0.0"})


def _strip_markdown_links(message: str) -> str:
    return _MARKDOWN_LINK_RE.sub(" ", message)


def _resolve_max_links(value: Any) -> int:
    if isinstance(value, bool):
        return DEFAULT_MAX_LINKS
    if isinstance(value, (int, float)):
        import math
        if math.isnan(value) or math.isinf(value):
            return DEFAULT_MAX_LINKS
        if value > 0:
            return int(value)
    return DEFAULT_MAX_LINKS


def _is_blocked_hostname_or_ip(hostname: str) -> bool:
    """Check if a hostname or IP is blocked for SSRF protection."""
    if not hostname:
        return True
    lowered = hostname.lower().strip()
    # Remove IPv6 brackets
    if lowered.startswith("[") and lowered.endswith("]"):
        lowered = lowered[1:-1]
    if lowered in _BLOCKED_HOSTNAMES:
        return True
    # Check if it's a private/loopback IP
    try:
        ip = ipaddress.ip_address(lowered)
        return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
    except ValueError:
        pass
    # Check .local domains
    if lowered.endswith(".local"):
        return True
    return False


def _is_allowed_url(raw: str) -> bool:
    try:
        parsed = urlparse(raw)
    except Exception:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    if _is_blocked_hostname_or_ip(parsed.hostname or ""):
        return False
    return True


def extract_links_from_message(
    message: str,
    opts: dict | None = None,
) -> list[str]:
    """Extract unique, SSRF-filtered bare HTTP(S) links from inbound text.

    Markdown links are ignored so display-only citations do not trigger fetches.
    """
    if not isinstance(message, str):
        return []
    source = message.strip()
    if not source:
        return []
    max_links = _resolve_max_links(opts.get("maxLinks") if opts else None)
    sanitized = _strip_markdown_links(source)
    seen: set[str] = set()
    results: list[str] = []
    for match in _BARE_LINK_RE.finditer(sanitized):
        raw = match.group(0).strip()
        if not raw:
            continue
        if not _is_allowed_url(raw):
            continue
        if raw in seen:
            continue
        seen.add(raw)
        results.append(raw)
        if len(results) >= max_links:
            break
    return results
