from __future__ import annotations

import os
import re
import socket
import time
from typing import Any


MISSING_SCOPE_PATTERN = re.compile(r"\bmissing scope:\s*[a-z0-9._-]+", re.IGNORECASE)


def _normalize_optional_string(value: Any) -> str | None:
    if isinstance(value, str) and len(value) > 0:
        return value
    return None


def _parse_int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _normalize_ws_url(value: str) -> str | None:
    trimmed = value.strip()
    if not trimmed:
        return None
    if not trimmed.startswith("ws://") and not trimmed.startswith("wss://"):
        return None
    return trimmed


def _is_loopback_host(host: str) -> bool:
    return host in ("127.0.0.1", "localhost", "::1")


def parse_timeout_ms(raw: Any, fallback_ms: int) -> int:
    if raw is None or raw == "":
        return fallback_ms
    try:
        return int(raw)
    except (ValueError, TypeError):
        return fallback_ms


def sanitize_ssh_target(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    trimmed = value.strip()
    if not trimmed:
        return None
    return re.sub(r"^ssh\s+", "", trimmed)


def resolve_probe_budget_ms(overall_ms: int, target: dict[str, Any]) -> int:
    if target.get("kind") == "sshTunnel":
        return min(2000, overall_ms)
    if target.get("active"):
        return overall_ms
    if target.get("kind") == "localLoopback":
        return min(800, overall_ms)
    url = target.get("url", "")
    if isinstance(url, str) and url:
        try:
            from urllib.parse import urlparse
            host = urlparse(url).hostname
            if host and not _is_loopback_host(host):
                return min(1500, overall_ms)
        except Exception:
            pass
    return overall_ms


def is_scope_limited_probe_failure(probe: dict[str, Any]) -> bool:
    if probe.get("ok") or probe.get("connectLatencyMs") is None:
        return False
    error = probe.get("error", "")
    if isinstance(error, str):
        return bool(MISSING_SCOPE_PATTERN.search(error))
    return False


def is_post_connect_probe_failure(probe: dict[str, Any]) -> bool:
    return not probe.get("ok", False) and probe.get("connectLatencyMs") is not None


def is_probe_reachable(probe: dict[str, Any]) -> bool:
    return probe.get("ok", False) or probe.get("connectLatencyMs") is not None


def _get_gateway_probe_capability(probe: dict[str, Any]) -> str:
    auth = probe.get("auth") or {}
    return auth.get("capability", "unknown")


def summarize_gateway_probe_capability(probes: list[dict[str, Any]]) -> str:
    priority = [
        "admin_capable",
        "write_capable",
        "read_only",
        "connected_no_operator_scope",
        "pairing_pending",
        "unknown",
    ]
    for capability in priority:
        for probe in probes:
            if _get_gateway_probe_capability(probe) == capability:
                return capability
    return "unknown"


def _format_gateway_probe_capability_label(capability: str) -> str:
    labels = {
        "admin_capable": "Capability: admin-capable",
        "write_capable": "Capability: write-capable",
        "read_only": "Capability: read-only",
        "connected_no_operator_scope": "Capability: connect-only",
        "pairing_pending": "Capability: pairing pending",
    }
    return labels.get(capability, "Capability: unknown")


def render_probe_summary_line(probe: dict[str, Any], rich: bool = True) -> str:
    capability = _format_gateway_probe_capability_label(_get_gateway_probe_capability(probe))
    if probe.get("ok"):
        latency = f"{probe['connectLatencyMs']}ms" if isinstance(probe.get("connectLatencyMs"), (int, float)) else "unknown"
        return f"Connect: ok ({latency}) · {capability} · Read probe: ok"

    detail = f" - {probe['error']}" if probe.get("error") else ""
    if probe.get("connectLatencyMs") is not None:
        latency = f"{probe['connectLatencyMs']}ms" if isinstance(probe.get("connectLatencyMs"), (int, float)) else "unknown"
        read_status = "Read probe: limited" if is_scope_limited_probe_failure(probe) else "Read probe: failed"
        return f"Connect: ok ({latency}) · {capability} · {read_status}{detail}"

    if _get_gateway_probe_capability(probe) == "pairing_pending":
        return f"Connect: blocked{detail} · {capability}"

    return f"Connect: failed{detail} · {capability}"


def render_target_header(target: dict[str, Any], rich: bool = True) -> str:
    kind = target.get("kind", "")
    if kind == "localLoopback":
        kind_label = "Local loopback"
    elif kind == "sshTunnel":
        kind_label = "Remote over SSH"
    elif kind == "configRemote":
        kind_label = "Remote (configured)" if target.get("active") else "Remote (configured, inactive)"
    else:
        kind_label = "URL (explicit)"
    url = target.get("url", "")
    return f"{kind_label} {url}"
