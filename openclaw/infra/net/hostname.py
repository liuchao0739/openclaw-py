from __future__ import annotations

from typing import Any


def hostname_from_url(url: str) -> str | None:
    from urllib.parse import urlparse
    try:
        parsed = urlparse(url)
        return parsed.hostname
    except Exception:
        return None


def is_local_hostname(hostname: str | None) -> bool:
    if not hostname:
        return False
    hostname_lower = hostname.lower()
    if hostname_lower in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
        return True
    if hostname_lower.endswith(".local"):
        return True
    try:
        import ipaddress
        addr = ipaddress.ip_address(hostname)
        return addr.is_loopback or addr.is_private or addr.is_link_local
    except ValueError:
        return False
