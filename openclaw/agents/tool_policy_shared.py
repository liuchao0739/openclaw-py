"""Shared runtime tool policy normalization."""

from __future__ import annotations

_TOOL_NAME_ALIASES: dict[str, str] = {
    "bash": "exec",
    "apply-patch": "apply_patch",
}

# Section-based groups (subset of TS CORE_TOOL_GROUPS for sandbox/policy expansion).
TOOL_GROUPS: dict[str, list[str]] = {
    "group:fs": ["read", "write", "edit", "apply_patch"],
    "group:runtime": ["exec", "process"],
    "group:sessions": [
        "sessions_list",
        "sessions_history",
        "sessions_send",
        "sessions_spawn",
        "sessions_yield",
        "session_status",
    ],
    "group:agents": ["subagents", "agents_list"],
}


def _normalize_lower(value: str) -> str:
    return value.strip().lower()


def normalize_tool_name(name: str) -> str:
    normalized = _normalize_lower(name)
    return _TOOL_NAME_ALIASES.get(normalized, normalized)


def normalize_tool_list(list_: list[str] | None) -> list[str]:
    if not list_:
        return []
    return [n for n in (normalize_tool_name(x) for x in list_) if n]


def _unique_strings(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def expand_tool_groups(list_: list[str] | None) -> list[str]:
    normalized = normalize_tool_list(list_)
    expanded: list[str] = []
    for value in normalized:
        group = TOOL_GROUPS.get(value)
        if group:
            expanded.extend(group)
        else:
            expanded.append(value)
    return _unique_strings(expanded)