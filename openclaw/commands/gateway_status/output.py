from __future__ import annotations

from typing import Any

from openclaw.commands.gateway_status.discovery import serialize_gateway_discovery_beacon
from openclaw.commands.gateway_status.helpers import (
    is_post_connect_probe_failure,
    is_probe_reachable,
    is_scope_limited_probe_failure,
    render_probe_summary_line,
    render_target_header,
    summarize_gateway_probe_capability,
)


NO_REACHABLE_GATEWAY_DIAGNOSTIC = (
    "No gateway answered any probe and Bonjour discovery returned no local gateways. "
    "Run `openclaw gateway status --deep --require-rpc` to inspect service state."
)


def _gateway_self_identity_key(entry: dict[str, Any]) -> str | None:
    self_info = entry.get("self")
    if not self_info:
        return None
    host = self_info.get("host", "")
    ip = self_info.get("ip", "")
    instance_id = self_info.get("instanceId", "")
    device_id = self_info.get("deviceId", "")
    discriminator = f"instance:{instance_id}" if instance_id else f"device:{device_id}" if device_id else ""
    if (not host and not ip) or not discriminator:
        return None
    return f"{host}\0{ip}\0{discriminator}"


def _has_multiple_reachable_gateway_identities(reachable: list[dict[str, Any]]) -> bool:
    if len(reachable) <= 1:
        return False
    identity_keys = [_gateway_self_identity_key(entry) for entry in reachable]
    if any(key is None for key in identity_keys):
        return True
    return len(set(identity_keys)) > 1


def _read_model_pricing_degraded_detail(health: Any) -> str | None:
    if not health or not isinstance(health, dict):
        return None
    model_pricing = health.get("modelPricing")
    if not model_pricing or not isinstance(model_pricing, dict):
        return None
    if model_pricing.get("state") != "degraded":
        return None
    detail = model_pricing.get("detail", "")
    return detail.strip() if isinstance(detail, str) and detail.strip() else "pricing bootstrap or refresh failed"


def pick_primary_probed_target(probed: list[dict[str, Any]]) -> dict[str, Any] | None:
    reachable = [e for e in probed if is_probe_reachable(e.get("probe", {}))]
    for kind in ["explicit", "sshTunnel", "configRemote", "localLoopback"]:
        for entry in reachable:
            if entry.get("target", {}).get("kind") == kind:
                return entry
    return None


def build_gateway_status_warnings(
    probed: list[dict[str, Any]],
    ssh_target: str | None = None,
    ssh_tunnel_started: bool = False,
    ssh_tunnel_error: str | None = None,
    local_tls_load_error: str | None = None,
    discovery_count: int = 0,
) -> list[dict[str, Any]]:
    reachable = [e for e in probed if is_probe_reachable(e.get("probe", {}))]
    degraded_scope_limited = [e for e in probed if is_scope_limited_probe_failure(e.get("probe", {}))]
    degraded_detail_failed = [
        e for e in probed
        if is_post_connect_probe_failure(e.get("probe", {})) and not is_scope_limited_probe_failure(e.get("probe", {}))
    ]
    warnings: list[dict[str, Any]] = []

    if ssh_target and not ssh_tunnel_started:
        msg = f"SSH tunnel failed: {ssh_tunnel_error}" if ssh_tunnel_error else "SSH tunnel failed to start; falling back to direct probes."
        warnings.append({"code": "ssh_tunnel_failed", "message": msg})

    if local_tls_load_error:
        warnings.append({
            "code": "local_tls_runtime_unavailable",
            "message": f"Local gateway TLS is enabled but OpenClaw could not load the local certificate fingerprint: {local_tls_load_error}",
            "targetIds": ["localLoopback"],
        })

    if len(reachable) == 0 and discovery_count == 0:
        warnings.append({
            "code": "no_gateway_reachable",
            "message": NO_REACHABLE_GATEWAY_DIAGNOSTIC,
            "targetIds": [e.get("target", {}).get("id") for e in probed],
        })

    if _has_multiple_reachable_gateway_identities(reachable):
        warnings.append({
            "code": "multiple_gateways",
            "message": "Unconventional setup: multiple reachable gateway identities detected.",
            "targetIds": [e.get("target", {}).get("id") for e in reachable],
        })

    for result in probed:
        auth_diags = result.get("authDiagnostics", [])
        if not auth_diags or is_probe_reachable(result.get("probe", {})):
            continue
        for diagnostic in auth_diags:
            warnings.append({
                "code": "auth_secretref_unresolved",
                "message": diagnostic,
                "targetIds": [result.get("target", {}).get("id")],
            })

    for result in degraded_scope_limited:
        warnings.append({
            "code": "probe_scope_limited",
            "message": "Read-probe diagnostics are limited by gateway scopes.",
            "targetIds": [result.get("target", {}).get("id")],
        })

    for result in degraded_detail_failed:
        detail = f": {result.get('probe', {}).get('error', '')}" if result.get("probe", {}).get("error") else "."
        warnings.append({
            "code": "probe_detail_failed",
            "message": f"Gateway accepted the WebSocket connection, but follow-up read diagnostics failed{detail}",
            "targetIds": [result.get("target", {}).get("id")],
        })

    for result in reachable:
        detail = _read_model_pricing_degraded_detail(result.get("probe", {}).get("health"))
        if not detail:
            continue
        warnings.append({
            "code": "model_pricing_degraded",
            "message": f"Model pricing warning: optional pricing refresh degraded: {detail}",
            "targetIds": [result.get("target", {}).get("id")],
        })

    return warnings


def write_gateway_status_text(
    runtime: dict[str, Any],
    probed: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
    discovery: list[dict[str, Any]] | None = None,
    overall_timeout_ms: int = 10000,
    wide_area_domain: str | None = None,
) -> None:
    rt = runtime or {}
    reachable = [e for e in probed if is_probe_reachable(e.get("probe", {}))]
    ok = len(reachable) > 0
    capability = summarize_gateway_probe_capability([e.get("probe", {}) for e in reachable])

    if rt.get("log"):
        rt["log"]("Gateway Status")
        rt["log"](f"Reachable: {'yes' if ok else 'no'}")
        rt["log"](f"Capability: {capability.replace('_', '-')}")
        rt["log"](f"Probe budget: {overall_timeout_ms}ms")

    if warnings and rt.get("log"):
        rt["log"]("")
        rt["log"]("Warning:")
        for w in warnings:
            rt["log"](f"- {w['message']}")

    if rt.get("log"):
        rt["log"]("")
        rt["log"]("Discovery (this machine)")
        discovery_list = discovery or []
        rt["log"](f"Found {len(discovery_list)} gateway(s) via Bonjour")

    if rt.get("log"):
        rt["log"]("")
        rt["log"]("Targets")
        for result in probed:
            rt["log"](render_target_header(result.get("target", {})))
            rt["log"](f"  {render_probe_summary_line(result.get('probe', {}))}")

    if not ok and rt.get("exit"):
        rt["exit"](1)
