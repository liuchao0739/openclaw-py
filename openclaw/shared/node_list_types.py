"""Node list types for gateway node-list endpoints."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class NodeListNode:
    node_id: str
    display_name: str | None = None
    platform: str | None = None
    version: str | None = None
    core_version: str | None = None
    ui_version: str | None = None
    client_id: str | None = None
    client_mode: str | None = None
    remote_ip: str | None = None
    device_family: str | None = None
    model_identifier: str | None = None
    path_env: str | None = None
    caps: list[str] | None = None
    commands: list[str] | None = None
    permissions: dict[str, bool] | None = None
    approval_state: str | None = None
    pending_request_id: str | None = None
    pending_declared_caps: list[str] | None = None
    pending_declared_commands: list[str] | None = None
    pending_declared_permissions: dict[str, bool] | None = None
    paired: bool | None = None
    connected: bool | None = None
    connected_at_ms: int | None = None
    last_seen_at_ms: int | None = None
    last_seen_reason: str | None = None
    approved_at_ms: int | None = None


@dataclass
class PendingRequest:
    request_id: str
    node_id: str
    display_name: str | None = None
    platform: str | None = None
    version: str | None = None
    core_version: str | None = None
    ui_version: str | None = None
    remote_ip: str | None = None
    ts: int = 0
    commands: list[str] | None = None


@dataclass
class PairedNode:
    node_id: str
    token: str | None = None
    display_name: str | None = None
    platform: str | None = None
    version: str | None = None
    core_version: str | None = None
    ui_version: str | None = None
    remote_ip: str | None = None
    permissions: dict[str, bool] | None = None
    created_at_ms: int | None = None
    approved_at_ms: int | None = None
    last_connected_at_ms: int | None = None
    last_seen_at_ms: int | None = None
    last_seen_reason: str | None = None


@dataclass
class PairingList:
    pending: list[PendingRequest]
    paired: list[PairedNode]
