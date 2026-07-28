"""Tailscale status helpers for parsing and validating status payloads."""

from __future__ import annotations

import json
import re
import subprocess
import shutil
from typing import Any, Callable


_TAILSCALE_STATUS_COMMAND_CANDIDATES = [
    "tailscale",
    "/Applications/Tailscale.app/Contents/MacOS/Tailscale",
]


def _parse_possibly_noisy_status(raw: str) -> dict[str, Any] | None:
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        return json.loads(raw[start : end + 1])
    except (json.JSONDecodeError, TypeError):
        return None


def _extract_tailnet_host_from_status_json(raw: str) -> str | None:
    parsed = _parse_possibly_noisy_status(raw)
    if not parsed:
        return None
    self_info = parsed.get("Self")
    if isinstance(self_info, dict):
        dns = self_info.get("DNSName")
        if isinstance(dns, str) and len(dns) > 0:
            return dns.rstrip(".")
        ips = self_info.get("TailscaleIPs", [])
        if isinstance(ips, list) and len(ips) > 0:
            first = ips[0]
            return first if isinstance(first, str) else None
    return None


def resolve_tailscale_published_host(
    tailscale_mode: str,
    tailnet_host: str | None,
    service_name: str | None = None,
) -> str | None:
    if not tailnet_host:
        return None
    host = tailnet_host.strip()
    if not host:
        return None
    if tailscale_mode == "serve":
        service = service_name.strip() if isinstance(service_name, str) else None
        if not service:
            return host
    if re.match(r"^[\d.:]+$", host):
        return None
    bare_service = (service or "").removeprefix("svc:")
    suffix = ".".join(host.split(".")[1:])
    return f"{bare_service}.{suffix}" if suffix else None


async def resolve_tailnet_host_with_runner(
    run_command_with_timeout: Callable[[list[str], dict[str, Any]], Any] | None = None,
) -> str | None:
    if run_command_with_timeout is None:
        return None
    for candidate in _TAILSCALE_STATUS_COMMAND_CANDIDATES:
        if not shutil.which(candidate) and candidate != "tailscale":
            continue
        try:
            result = await run_command_with_timeout([candidate, "status", "--json"], {"timeoutMs": 5000})
            if result.get("code") != 0:
                continue
            raw = result.get("stdout", "").strip()
            if not raw:
                continue
            host = _extract_tailnet_host_from_status_json(raw)
            if host:
                return host
        except Exception:
            continue
    return None
