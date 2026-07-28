from __future__ import annotations

import math
from typing import Any, Literal, TypedDict

from ._normalization import normalize_optional_string

SUBAGENT_ROLES = ["orchestrator", "leaf"]
SUBAGENT_CONTROL_SCOPES = ["children", "none"]

SubagentRole = Literal["orchestrator", "leaf"]
SubagentControlScope = Literal["children", "none"]


class AcpSessionLineageMeta(TypedDict, total=False):
    sessionKey: str
    kind: str | None
    channel: str | None
    parentSessionId: str | None
    spawnedBy: str | None
    spawnDepth: int | None
    subagentRole: SubagentRole | None
    subagentControlScope: SubagentControlScope | None
    spawnedWorkspaceDir: str | None
    spawnedCwd: str | None


class AcpSessionLineageRow(TypedDict, total=False):
    key: str
    kind: str | None
    channel: str | None
    parentSessionKey: str | None
    spawnedBy: str | None
    spawnDepth: int | None
    subagentRole: str | None
    subagentControlScope: str | None
    spawnedWorkspaceDir: str | None
    spawnedCwd: str | None


def _read_integer(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value >= 0:
        return value
    if isinstance(value, float) and math.isfinite(value) and value == int(value) and value >= 0:
        return int(value)
    return None


def _read_enum(value: Any, allowed: list[str]) -> str | None:
    normalized = normalize_optional_string(value)
    if normalized is None:
        return None
    return normalized if normalized in allowed else None


def to_acp_session_lineage_meta(row: AcpSessionLineageRow) -> AcpSessionLineageMeta:
    session_key = normalize_optional_string(row.get("key")) or row.get("key", "")
    kind = normalize_optional_string(row.get("kind"))
    channel = normalize_optional_string(row.get("channel"))
    parent_session_id = normalize_optional_string(row.get("parentSessionKey")) or normalize_optional_string(
        row.get("spawnedBy")
    )
    spawned_by = normalize_optional_string(row.get("spawnedBy"))
    spawn_depth = _read_integer(row.get("spawnDepth"))
    subagent_role = _read_enum(row.get("subagentRole"), SUBAGENT_ROLES)
    subagent_control_scope = _read_enum(row.get("subagentControlScope"), SUBAGENT_CONTROL_SCOPES)
    spawned_workspace_dir = normalize_optional_string(row.get("spawnedWorkspaceDir"))
    spawned_cwd = normalize_optional_string(row.get("spawnedCwd"))

    result: AcpSessionLineageMeta = {"sessionKey": session_key}
    if kind:
        result["kind"] = kind
    if channel:
        result["channel"] = channel
    if parent_session_id:
        result["parentSessionId"] = parent_session_id
    if spawned_by:
        result["spawnedBy"] = spawned_by
    if spawn_depth is not None:
        result["spawnDepth"] = spawn_depth
    if subagent_role:
        result["subagentRole"] = subagent_role
    if subagent_control_scope:
        result["subagentControlScope"] = subagent_control_scope
    if spawned_workspace_dir:
        result["spawnedWorkspaceDir"] = spawned_workspace_dir
    if spawned_cwd:
        result["spawnedCwd"] = spawned_cwd
    return result