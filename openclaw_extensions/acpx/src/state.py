"""ACPX plugin state keys shared by runtime and doctor migration."""

from __future__ import annotations

from typing import Any, TypedDict

ACPX_PROCESS_LEASE_NAMESPACE = "process-leases"
ACPX_PROCESS_LEASE_MAX_ENTRIES = 4096
ACPX_LEGACY_PROCESS_LEASE_FILE = "process-leases.json"

ACPX_GATEWAY_INSTANCE_NAMESPACE = "gateway-instance"
ACPX_GATEWAY_INSTANCE_KEY = "current"
ACPX_GATEWAY_INSTANCE_MAX_ENTRIES = 1
ACPX_LEGACY_GATEWAY_INSTANCE_FILE = "gateway-instance-id"


class AcpxGatewayInstanceRecord(TypedDict):
    instanceId: str
    createdAt: int


def normalize_acpx_gateway_instance_record(
    value: Any,
) -> AcpxGatewayInstanceRecord | None:
    if not isinstance(value, dict):
        return None
    instance_id = value.get("instanceId")
    if not isinstance(instance_id, str) or not instance_id.strip():
        return None
    created_at_raw = value.get("createdAt")
    created_at = int(created_at_raw) if isinstance(created_at_raw, (int, float)) else 0
    return {
        "instanceId": instance_id.strip(),
        "createdAt": created_at,
    }
