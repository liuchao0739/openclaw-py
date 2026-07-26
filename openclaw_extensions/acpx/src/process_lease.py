"""Persistent lease store helpers for ACPX wrapper processes."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal, TypedDict

from openclaw_extensions.acpx.src.state import (
    ACPX_PROCESS_LEASE_MAX_ENTRIES,
    ACPX_PROCESS_LEASE_NAMESPACE,
)

OPENCLAW_ACPX_LEASE_ID_ENV = "OPENCLAW_ACPX_LEASE_ID"
OPENCLAW_GATEWAY_INSTANCE_ID_ENV = "OPENCLAW_GATEWAY_INSTANCE_ID"
OPENCLAW_ACPX_LEASE_ID_ARG = "--openclaw-acpx-lease-id"
OPENCLAW_GATEWAY_INSTANCE_ID_ARG = "--openclaw-gateway-instance-id"

AcpxProcessLeaseState = Literal["open", "closing", "closed", "lost"]


class AcpxProcessLease(TypedDict, total=False):
    lease_id: str
    gateway_instance_id: str
    session_key: str
    wrapper_root: str
    wrapper_path: str
    root_pid: int
    process_group_id: int
    command_hash: str
    started_at: int
    state: AcpxProcessLeaseState


class AcpxProcessLeaseFile(TypedDict):
    version: Literal[1]
    leases: list[AcpxProcessLease]


class OpenKeyedStoreOptions(TypedDict, total=False):
    namespace: str
    max_entries: int
    default_ttl_ms: int
    env: dict[str, str]


class PluginStateEntry(TypedDict):
    key: str
    value: Any
    created_at: int
    expires_at: int | None


class PluginStateKeyedStore:
    async def register(
        self,
        key: str,
        value: Any,
        *,
        ttl_ms: int | None = None,
    ) -> None: ...

    async def register_if_absent(
        self,
        key: str,
        value: Any,
        *,
        ttl_ms: int | None = None,
    ) -> bool: ...

    async def lookup(self, key: str) -> Any: ...

    async def delete(self, key: str) -> bool: ...

    async def entries(self) -> list[PluginStateEntry]: ...

    async def clear(self) -> None: ...


OpenKeyedStoreFactory = Callable[[OpenKeyedStoreOptions], PluginStateKeyedStore]


def normalize_acpx_process_lease(value: Any) -> AcpxProcessLease | None:
    if not isinstance(value, dict):
        return None
    required_fields = (
        ("leaseId", str),
        ("gatewayInstanceId", str),
        ("sessionKey", str),
        ("wrapperRoot", str),
        ("wrapperPath", str),
        ("rootPid", (int, float)),
        ("commandHash", str),
        ("startedAt", (int, float)),
    )
    for field_name, field_type in required_fields:
        field_value = value.get(field_name)
        if not isinstance(field_value, field_type):
            return None
    state = value.get("state")
    if state not in {"open", "closing", "closed", "lost"}:
        return None
    lease: AcpxProcessLease = {
        "leaseId": value["leaseId"],
        "gatewayInstanceId": value["gatewayInstanceId"],
        "sessionKey": value["sessionKey"],
        "wrapperRoot": value["wrapperRoot"],
        "wrapperPath": value["wrapperPath"],
        "rootPid": int(value["rootPid"]),
        "commandHash": value["commandHash"],
        "startedAt": int(value["startedAt"]),
        "state": state,
    }
    process_group_id = value.get("processGroupId")
    if isinstance(process_group_id, (int, float)):
        lease["processGroupId"] = int(process_group_id)
    return lease


def normalize_acpx_process_lease_file(value: Any) -> AcpxProcessLeaseFile:
    root = value if isinstance(value, dict) else {}
    raw_leases = root.get("leases")
    leases: list[AcpxProcessLease] = []
    if isinstance(raw_leases, list):
        for entry in raw_leases:
            lease = normalize_acpx_process_lease(entry)
            if lease is not None:
                leases.append(lease)
    return {"version": 1, "leases": leases}


def open_acpx_process_lease_state_store(
    open_keyed_store: OpenKeyedStoreFactory,
) -> PluginStateKeyedStore:
    return open_keyed_store(
        {
            "namespace": ACPX_PROCESS_LEASE_NAMESPACE,
            "maxEntries": ACPX_PROCESS_LEASE_MAX_ENTRIES,
        }
    )
