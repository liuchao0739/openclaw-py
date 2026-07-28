from __future__ import annotations

import os
import socket
from typing import Any


def _normalize_optional_string(value: Any) -> str | None:
    if isinstance(value, str) and len(value) > 0:
        return value
    return None


def infer_ssh_target_from_remote_url(raw_url: str | None) -> str | None:
    if not isinstance(raw_url, str):
        return None
    trimmed = _normalize_optional_string(raw_url) or ""
    if not trimmed:
        return None
    try:
        from urllib.parse import urlparse
        host = urlparse(trimmed).hostname
    except Exception:
        return None
    if not host:
        return None
    user = os.environ.get("USER", "") or ""
    return f"{user}@{host}" if user else host


def _build_ssh_target(user: str | None = None, host: str | None = None, port: int | None = None) -> str | None:
    host_val = _normalize_optional_string(host) or ""
    if not host_val:
        return None
    user_val = _normalize_optional_string(user) or ""
    base = f"{user_val}@{host_val}" if user_val else host_val
    port_val = port or 22
    if port_val and port_val != 22:
        return f"{base}:{port_val}"
    return base


def pick_auto_ssh_target_from_discovery(
    discovery: list[dict[str, Any]],
    ssh_user: str | None = None,
) -> str | None:
    for beacon in discovery:
        ssh_target = beacon.get("sshTarget")
        if ssh_target:
            return ssh_target
    return None


def serialize_gateway_discovery_beacon(beacon: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": beacon.get("id"),
        "name": beacon.get("name"),
        "host": beacon.get("host"),
        "port": beacon.get("port"),
        "sshTarget": beacon.get("sshTarget"),
        "instanceId": beacon.get("instanceId"),
        "deviceId": beacon.get("deviceId"),
    }
