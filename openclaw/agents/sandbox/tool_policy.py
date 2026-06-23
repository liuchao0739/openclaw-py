"""Sandbox tool policy resolver."""

from __future__ import annotations

from typing import Any, Literal

from openclaw.agents.glob_pattern import compile_glob_patterns, matches_any_glob_pattern
from openclaw.agents.sandbox.constants import DEFAULT_TOOL_ALLOW, DEFAULT_TOOL_DENY
from openclaw.agents.sandbox.types import (
    SandboxToolPolicy,
    SandboxToolPolicyResolved,
    SandboxToolPolicySource,
)
from openclaw.agents.tool_policy_shared import expand_tool_groups, normalize_tool_name


def _build_source(*, scope: Literal["agent", "global", "default"], key: str) -> SandboxToolPolicySource:
    return {"source": scope, "key": key}


def _pick_configured_list(
    *,
    agent: list[str] | None,
    global_: list[str] | None,
    allow_key: str,
) -> tuple[list[str] | None, SandboxToolPolicySource]:
    if isinstance(agent, list):
        return agent, _build_source(scope="agent", key=f"agents.list[].tools.sandbox.tools.{allow_key}")
    if isinstance(global_, list):
        return global_, _build_source(scope="global", key=f"tools.sandbox.tools.{allow_key}")
    return None, _build_source(scope="default", key=f"tools.sandbox.tools.{allow_key}")


def _unique_strings(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _merge_allowlist(base: list[str] | None, extra: list[str] | None) -> list[str]:
    if isinstance(base, list):
        if len(base) == 0:
            return []
        if not extra:
            return list(base)
        return _unique_strings([*base, *extra])
    if extra:
        return _unique_strings([*DEFAULT_TOOL_ALLOW, *extra])
    return list(DEFAULT_TOOL_ALLOW)


def _resolve_explicit_reallow(*, allow: list[str] | None, also_allow: list[str] | None) -> list[str]:
    return _unique_strings([*(allow or []), *(also_allow or [])])


def _filter_default_deny_for_explicit_allows(
    *,
    deny: list[str],
    explicit_allow_patterns: list[str],
) -> list[str]:
    if not explicit_allow_patterns:
        return list(deny)
    allow_patterns = compile_glob_patterns(
        raw=expand_tool_groups(explicit_allow_patterns),
        normalize=normalize_tool_name,
    )
    if not allow_patterns:
        return list(deny)
    return [
        tool
        for tool in deny
        if not matches_any_glob_pattern(normalize_tool_name(tool), allow_patterns)
    ]


def _expand_resolved_policy(policy: SandboxToolPolicy) -> SandboxToolPolicy:
    expanded_deny = expand_tool_groups(policy.get("deny"))
    expanded_allow = expand_tool_groups(policy.get("allow"))
    deny_lower = [normalize_tool_name(t) for t in expanded_deny]
    allow_lower = [normalize_tool_name(t) for t in expanded_allow]
    if (
        len(expanded_allow) > 0
        and "image" not in deny_lower
        and "image" not in allow_lower
    ):
        expanded_allow = [*expanded_allow, "image"]
    return {"allow": expanded_allow, "deny": expanded_deny}


def _pick_allow_source(
    *,
    allow: SandboxToolPolicySource,
    allow_defined: bool,
    also_allow: SandboxToolPolicySource | None,
) -> SandboxToolPolicySource:
    if allow_defined and allow["source"] == "agent":
        return allow
    if also_allow and also_allow["source"] == "agent":
        return also_allow
    if allow_defined and allow["source"] == "global":
        return allow
    if also_allow and also_allow["source"] == "global":
        return also_allow
    return allow


def classify_tool_against_sandbox_tool_policy(
    name: str,
    policy: SandboxToolPolicy | None,
) -> dict[str, bool]:
    if not policy:
        return {"blockedByDeny": False, "blockedByAllow": False}
    normalized = normalize_tool_name(name)
    deny = compile_glob_patterns(
        raw=expand_tool_groups(policy.get("deny")),
        normalize=normalize_tool_name,
    )
    blocked_by_deny = matches_any_glob_pattern(normalized, deny)
    allow = compile_glob_patterns(
        raw=expand_tool_groups(policy.get("allow")),
        normalize=normalize_tool_name,
    )
    blocked_by_allow = (
        not blocked_by_deny and len(allow) > 0 and not matches_any_glob_pattern(normalized, allow)
    )
    return {"blockedByDeny": blocked_by_deny, "blockedByAllow": blocked_by_allow}


def is_tool_allowed(policy: SandboxToolPolicy, name: str) -> bool:
    result = classify_tool_against_sandbox_tool_policy(name, policy)
    return not result["blockedByDeny"] and not result["blockedByAllow"]


def _resolve_agent_sandbox_tools(cfg: dict[str, Any] | None, agent_id: str | None) -> dict[str, Any] | None:
    if not cfg or not agent_id:
        return None
    agents = cfg.get("agents")
    if not isinstance(agents, dict):
        return None
    agent_list = agents.get("list")
    if not isinstance(agent_list, list):
        return None
    for entry in agent_list:
        if not isinstance(entry, dict):
            continue
        if str(entry.get("id", "")).strip() == agent_id.strip():
            tools = entry.get("tools")
            if isinstance(tools, dict):
                sandbox = tools.get("sandbox")
                if isinstance(sandbox, dict):
                    inner = sandbox.get("tools")
                    if isinstance(inner, dict):
                        return inner
    return None


def resolve_sandbox_tool_policy_for_agent(
    cfg: dict[str, Any] | None = None,
    agent_id: str | None = None,
) -> SandboxToolPolicyResolved:
    agent_policy = _resolve_agent_sandbox_tools(cfg, agent_id)
    global_tools: dict[str, Any] | None = None
    if cfg and isinstance(cfg.get("tools"), dict):
        sandbox = cfg["tools"].get("sandbox")
        if isinstance(sandbox, dict) and isinstance(sandbox.get("tools"), dict):
            global_tools = sandbox["tools"]

    allow_vals, allow_src = _pick_configured_list(
        agent=agent_policy.get("allow") if agent_policy else None,
        global_=global_tools.get("allow") if global_tools else None,
        allow_key="allow",
    )
    also_vals, also_src = _pick_configured_list(
        agent=agent_policy.get("alsoAllow") if agent_policy else None,
        global_=global_tools.get("alsoAllow") if global_tools else None,
        allow_key="alsoAllow",
    )
    deny_vals, deny_src = _pick_configured_list(
        agent=agent_policy.get("deny") if agent_policy else None,
        global_=global_tools.get("deny") if global_tools else None,
        allow_key="deny",
    )

    explicit = _resolve_explicit_reallow(allow=allow_vals, also_allow=also_vals)
    resolved_allow = _merge_allowlist(allow_vals, also_vals)
    if isinstance(deny_vals, list):
        resolved_deny = list(deny_vals)
    else:
        resolved_deny = _filter_default_deny_for_explicit_allows(
            deny=list(DEFAULT_TOOL_DENY),
            explicit_allow_patterns=explicit,
        )

    expanded = _expand_resolved_policy({"allow": resolved_allow, "deny": resolved_deny})
    also_source = also_src if isinstance(also_vals, list) else None

    return {
        "allow": expanded.get("allow") or [],
        "deny": expanded.get("deny") or [],
        "sources": {
            "allow": _pick_allow_source(
                allow=allow_src,
                allow_defined=isinstance(allow_vals, list),
                also_allow=also_source,
            ),
            "deny": deny_src,
        },
    }