from __future__ import annotations

import math
from typing import Any

DEFAULT_AGENT_MAX_CONCURRENT = 4
DEFAULT_SUBAGENT_MAX_CONCURRENT = 8
DEFAULT_SUBAGENT_MAX_CHILDREN_PER_AGENT = 5
DEFAULT_SUBAGENT_ARCHIVE_AFTER_MINUTES = 60
DEFAULT_SUBAGENT_MAX_SPAWN_DEPTH = 1


def resolve_agent_max_concurrent(cfg: dict[str, Any] | None = None) -> int:
    raw = (cfg or {}).get("agents", {}).get("defaults", {}).get("maxConcurrent")
    if isinstance(raw, (int, float)) and math.isfinite(raw):
        return max(1, int(raw))
    return DEFAULT_AGENT_MAX_CONCURRENT


def resolve_subagent_max_concurrent(cfg: dict[str, Any] | None = None) -> int:
    raw = (cfg or {}).get("agents", {}).get("defaults", {}).get("subagents", {}).get("maxConcurrent")
    if isinstance(raw, (int, float)) and math.isfinite(raw):
        return max(1, int(raw))
    return DEFAULT_SUBAGENT_MAX_CONCURRENT


def resolve_subagent_max_children_per_agent(cfg: dict[str, Any] | None = None) -> int:
    raw = (cfg or {}).get("agents", {}).get("defaults", {}).get("subagents", {}).get("maxChildrenPerAgent")
    if isinstance(raw, (int, float)) and math.isfinite(raw):
        return max(1, int(raw))
    return DEFAULT_SUBAGENT_MAX_CHILDREN_PER_AGENT


def resolve_subagent_archive_after_minutes(cfg: dict[str, Any] | None = None) -> int:
    raw = (cfg or {}).get("agents", {}).get("defaults", {}).get("subagents", {}).get("archiveAfterMinutes")
    if isinstance(raw, (int, float)) and math.isfinite(raw):
        return max(1, int(raw))
    return DEFAULT_SUBAGENT_ARCHIVE_AFTER_MINUTES


def resolve_subagent_max_spawn_depth(cfg: dict[str, Any] | None = None) -> int:
    raw = (cfg or {}).get("agents", {}).get("defaults", {}).get("subagents", {}).get("maxSpawnDepth")
    if isinstance(raw, (int, float)) and math.isfinite(raw):
        return max(1, int(raw))
    return DEFAULT_SUBAGENT_MAX_SPAWN_DEPTH
