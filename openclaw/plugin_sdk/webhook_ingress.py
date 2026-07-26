"""Public SDK subpath for webhook ingress request helpers."""

from __future__ import annotations

import ipaddress
from collections.abc import Mapping, Sequence
from typing import Any


def _normalize_ip(raw: str | None) -> str | None:
    if raw is None:
        return None
    trimmed = raw.strip()
    if not trimmed:
        return None
    if trimmed.startswith("[") and "]" in trimmed:
        trimmed = trimmed[1 : trimmed.index("]")]
    elif trimmed.count(":") == 1 and "." in trimmed:
        host, _port = trimmed.rsplit(":", 1)
        if host.count(".") == 3:
            trimmed = host
    try:
        return str(ipaddress.ip_address(trimmed))
    except ValueError:
        return None


def _is_loopback_address(ip: str | None) -> bool:
    normalized = _normalize_ip(ip)
    if normalized is None:
        return False
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


def _is_ip_in_cidr(ip: str, candidate: str) -> bool:
    trimmed = candidate.strip()
    if not trimmed:
        return False
    try:
        if "/" in trimmed:
            return ipaddress.ip_address(ip) in ipaddress.ip_network(trimmed, strict=False)
        return ip == _normalize_ip(trimmed)
    except ValueError:
        return False


def is_trusted_proxy_address(ip: str | None, trusted_proxies: Sequence[str] | None) -> bool:
    normalized = _normalize_ip(ip)
    if normalized is None or not trusted_proxies:
        return False
    return any(_is_ip_in_cidr(normalized, proxy) for proxy in trusted_proxies)


def _parse_real_ip(real_ip: str | None) -> str | None:
    return _normalize_ip(real_ip)


def _resolve_forwarded_client_ip(
    *,
    forwarded_for: str | None,
    trusted_proxies: Sequence[str] | None,
) -> str | None:
    if not trusted_proxies:
        return None
    forwarded_chain: list[str] = []
    for entry in (forwarded_for or "").split(","):
        normalized = _normalize_ip(entry)
        if normalized is not None:
            forwarded_chain.append(normalized)
    if not forwarded_chain:
        return None
    for hop in reversed(forwarded_chain):
        if _is_loopback_address(hop):
            continue
        if not is_trusted_proxy_address(hop, trusted_proxies):
            return hop
    return None


def resolve_client_ip(
    *,
    remote_addr: str | None = None,
    forwarded_for: str | None = None,
    real_ip: str | None = None,
    trusted_proxies: Sequence[str] | None = None,
    allow_real_ip_fallback: bool = False,
) -> str | None:
    remote = _normalize_ip(remote_addr)
    if remote is None:
        return None
    if not is_trusted_proxy_address(remote, trusted_proxies):
        return remote
    forwarded_ip = _resolve_forwarded_client_ip(
        forwarded_for=forwarded_for,
        trusted_proxies=trusted_proxies,
    )
    if forwarded_ip is not None:
        return forwarded_ip
    if allow_real_ip_fallback:
        return _parse_real_ip(real_ip)
    return None


def _header_value(value: str | Sequence[str] | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return value[0] if value else None


def resolve_request_client_ip(
    req: Mapping[str, Any] | Any | None = None,
    trusted_proxies: Sequence[str] | None = None,
    allow_real_ip_fallback: bool = False,
) -> str | None:
    if req is None:
        return None
    headers = getattr(req, "headers", None) or (
        req.get("headers") if isinstance(req, Mapping) else None
    )
    socket = getattr(req, "socket", None) or (
        req.get("socket") if isinstance(req, Mapping) else None
    )
    remote_address = None
    if socket is not None:
        remote_address = getattr(socket, "remoteAddress", None) or getattr(
            socket, "remote_address", None
        )
        if remote_address is None and isinstance(socket, Mapping):
            remote_address = socket.get("remoteAddress") or socket.get("remote_address")
    forwarded_for = None
    real_ip = None
    if isinstance(headers, Mapping):
        forwarded_for = _header_value(headers.get("x-forwarded-for"))
        real_ip = _header_value(headers.get("x-real-ip"))
    return resolve_client_ip(
        remote_addr=remote_address,
        forwarded_for=forwarded_for,
        real_ip=real_ip,
        trusted_proxies=trusted_proxies,
        allow_real_ip_fallback=allow_real_ip_fallback,
    )


__all__ = [
    "is_trusted_proxy_address",
    "resolve_client_ip",
    "resolve_request_client_ip",
]
