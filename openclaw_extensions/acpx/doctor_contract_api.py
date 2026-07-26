"""ACPX doctor contract migrates shipped plugin-owned runtime state."""

from __future__ import annotations

import os
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, TypedDict

from openclaw_extensions.acpx.src.process_lease import (
    AcpxProcessLease,
    normalize_acpx_process_lease,
    normalize_acpx_process_lease_file,
    open_acpx_process_lease_state_store,
)
from openclaw_extensions.acpx.src.state import (
    ACPX_GATEWAY_INSTANCE_KEY,
    ACPX_GATEWAY_INSTANCE_MAX_ENTRIES,
    ACPX_GATEWAY_INSTANCE_NAMESPACE,
    ACPX_LEGACY_GATEWAY_INSTANCE_FILE,
    ACPX_LEGACY_PROCESS_LEASE_FILE,
    normalize_acpx_gateway_instance_record,
)


class PluginDoctorStateMigrationDetection(TypedDict):
    preview: list[str]


class PluginDoctorStateMigrationContext(TypedDict):
    open_plugin_state_keyed_store: Callable[..., Any]


class PluginDoctorStateMigrationParams(TypedDict):
    config: Any
    env: dict[str, str]
    state_dir: str
    oauth_dir: str
    context: PluginDoctorStateMigrationContext


class PluginDoctorStateMigration(TypedDict):
    id: str
    label: str
    detect_legacy_state: Callable[
        [PluginDoctorStateMigrationParams],
        PluginDoctorStateMigrationDetection | None | Awaitable[PluginDoctorStateMigrationDetection | None],
    ]
    migrate_legacy_state: Callable[
        [PluginDoctorStateMigrationParams],
        dict[str, list[str]] | Awaitable[dict[str, list[str]]],
    ]


def _resolve_legacy_gateway_instance_path(state_dir: str) -> Path:
    return Path(state_dir) / ACPX_LEGACY_GATEWAY_INSTANCE_FILE


def _resolve_legacy_process_lease_path(state_dir: str) -> Path:
    return Path(state_dir) / "acpx" / ACPX_LEGACY_PROCESS_LEASE_FILE


async def _file_exists(file_path: Path) -> bool:
    try:
        return file_path.is_file()
    except OSError:
        return False


async def _read_legacy_gateway_instance_id(file_path: Path) -> str | None:
    try:
        value = file_path.read_text(encoding="utf-8").strip()
        return value or None
    except OSError:
        return None


async def _read_legacy_open_process_leases(file_path: Path) -> list[AcpxProcessLease]:
    try:
        import json

        lease_file = normalize_acpx_process_lease_file(
            json.loads(file_path.read_text(encoding="utf-8"))
        )
        return [
            lease
            for lease in lease_file["leases"]
            if lease.get("state") in {"open", "closing"}
        ]
    except (OSError, json.JSONDecodeError):
        return []


async def _archive_legacy_source(
    *,
    file_path: Path,
    label: str,
    changes: list[str],
    warnings: list[str],
) -> None:
    archived_path = Path(f"{file_path}.migrated")
    if await _file_exists(archived_path):
        warnings.append(
            "Left migrated ACPX "
            f"{label} source in place because {archived_path} already exists"
        )
        return
    try:
        os.rename(file_path, archived_path)
        changes.append(f"Archived ACPX {label} legacy source -> {archived_path}")
    except OSError as err:
        warnings.append(f"Failed archiving ACPX {label} legacy source: {err!s}")


async def _detect_legacy_state(
    params: PluginDoctorStateMigrationParams,
) -> PluginDoctorStateMigrationDetection | None:
    gateway_instance_id = await _read_legacy_gateway_instance_id(
        _resolve_legacy_gateway_instance_path(params["state_dir"])
    )
    open_leases = await _read_legacy_open_process_leases(
        _resolve_legacy_process_lease_path(params["state_dir"])
    )
    if not gateway_instance_id and not open_leases:
        return None
    preview: list[str] = []
    if gateway_instance_id:
        preview.append(
            "- ACPX gateway instance id: "
            f"{_resolve_legacy_gateway_instance_path(params['state_dir'])} -> plugin state "
            f"({ACPX_GATEWAY_INSTANCE_NAMESPACE})"
        )
    if open_leases:
        preview.append(
            "- ACPX process leases: "
            f"{_resolve_legacy_process_lease_path(params['state_dir'])} -> plugin state "
            f"({len(open_leases)} open lease(s))"
        )
    return {"preview": preview}


async def _migrate_legacy_state(
    params: PluginDoctorStateMigrationParams,
) -> dict[str, list[str]]:
    changes: list[str] = []
    warnings: list[str] = []
    gateway_instance_path = _resolve_legacy_gateway_instance_path(params["state_dir"])
    gateway_instance_id = await _read_legacy_gateway_instance_id(gateway_instance_path)
    process_lease_path = _resolve_legacy_process_lease_path(params["state_dir"])
    open_leases = await _read_legacy_open_process_leases(process_lease_path)
    process_lease_store = open_acpx_process_lease_state_store(
        params["context"]["open_plugin_state_keyed_store"]
    )
    gateway_store = params["context"]["open_plugin_state_keyed_store"](
        {
            "namespace": ACPX_GATEWAY_INSTANCE_NAMESPACE,
            "maxEntries": ACPX_GATEWAY_INSTANCE_MAX_ENTRIES,
        }
    )
    existing_gateway = normalize_acpx_gateway_instance_record(
        await gateway_store.lookup(ACPX_GATEWAY_INSTANCE_KEY)
    )
    existing_live_leases = [
        lease
        for entry in await process_lease_store.entries()
        if (lease := normalize_acpx_process_lease(entry["value"])) is not None
        and lease.get("state") in {"open", "closing"}
    ]
    lease_gateway_ids = {lease["gatewayInstanceId"] for lease in open_leases}
    only_lease_gateway_id = next(iter(lease_gateway_ids)) if len(lease_gateway_ids) == 1 else None
    can_adopt_legacy_gateway = bool(
        existing_gateway
        and gateway_instance_id
        and existing_gateway["instanceId"] != gateway_instance_id
        and only_lease_gateway_id == gateway_instance_id
        and not existing_live_leases
    )
    if can_adopt_legacy_gateway or not existing_gateway:
        canonical_gateway_instance_id = gateway_instance_id or only_lease_gateway_id
    else:
        canonical_gateway_instance_id = existing_gateway["instanceId"]

    if open_leases and (
        not canonical_gateway_instance_id
        or any(
            lease_gateway_id != canonical_gateway_instance_id
            for lease_gateway_id in lease_gateway_ids
        )
    ):
        warnings.append(
            "Skipped ACPX process lease migration because legacy leases do not match "
            "the canonical gateway instance id; left legacy sources in place for manual cleanup"
        )
        return {"changes": changes, "warnings": warnings}

    if can_adopt_legacy_gateway and canonical_gateway_instance_id or canonical_gateway_instance_id and not existing_gateway:
        await gateway_store.register(
            ACPX_GATEWAY_INSTANCE_KEY,
            {
                "instanceId": canonical_gateway_instance_id,
                "createdAt": int(time.time() * 1000),
            },
        )
        changes.append("Migrated ACPX gateway instance id -> plugin state")
    elif (
        gateway_instance_id
        and existing_gateway
        and existing_gateway["instanceId"] != gateway_instance_id
    ):
        warnings.append(
            "Skipped ACPX gateway instance id import because plugin state already differs"
        )

    if gateway_instance_id:
        await _archive_legacy_source(
            file_path=gateway_instance_path,
            label="gateway-instance-id",
            changes=changes,
            warnings=warnings,
        )

    if open_leases:
        imported = 0
        already_present = 0
        for lease in open_leases:
            inserted = await process_lease_store.register_if_absent(lease["leaseId"], lease)
            if inserted:
                imported += 1
            else:
                already_present += 1
        changes.append(
            "Migrated ACPX process leases -> plugin state "
            f"({imported} imported, {already_present} already present)"
        )
        await _archive_legacy_source(
            file_path=process_lease_path,
            label="process-leases",
            changes=changes,
            warnings=warnings,
        )

    return {"changes": changes, "warnings": warnings}


state_migrations: list[PluginDoctorStateMigration] = [
    {
        "id": "acpx-runtime-state-to-plugin-state",
        "label": "ACPX runtime state",
        "detect_legacy_state": _detect_legacy_state,
        "migrate_legacy_state": _migrate_legacy_state,
    }
]
