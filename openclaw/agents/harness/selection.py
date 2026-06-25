"""Selects and invokes native agent harnesses for embedded run attempts.

Plugin harness selection, tool-policy enforcement, and CLI runtime alias
resolution are ported with lazy dependency resolution. When a dependency
module is not yet ported, the selection falls back gracefully.
"""

from __future__ import annotations

from functools import cmp_to_key
from typing import Any, Literal, TypedDict

from openclaw.agents.harness.builtin_openclaw import create_openclaw_agent_harness
from openclaw.agents.harness.errors import MissingAgentHarnessError
from openclaw.agents.harness.lifecycle import run_agent_harness_lifecycle_attempt
from openclaw.agents.harness.policy import (
    AgentHarnessPolicy,
    resolve_agent_harness_policy as resolve_configured_agent_harness_policy,
)
from openclaw.agents.harness.registry import (
    get_registered_agent_harness,
    list_registered_agent_harnesses,
)

PLUGIN_HARNESS_SENDER_DENY_ALL_PROMPT = (
    "Tool and file actions are disabled for this sender by chat policy. "
    "If asked to edit files or use tools, say this sender is not allowed by policy; "
    "do not imply retrying will help."
)
PLUGIN_HARNESS_GROUP_DENY_ALL_PROMPT = (
    "Tool and file actions are disabled for this chat by chat policy. "
    "If asked to edit files or use tools, say this chat is not allowed by policy."
)
PLUGIN_HARNESS_RUNTIME_DENY_ALL_PROMPT = (
    "Tool and file actions are disabled by runtime policy. "
    "If asked to edit files or use tools, say tools are disabled by policy."
)


class AgentHarnessSelectionCandidate(TypedDict, total=False):
    id: str
    label: str
    pluginId: str
    supported: bool
    priority: int
    reason: str


SelectedReason = Literal[
    "forced_openclaw",
    "forced_plugin",
    "implicit_plugin_unavailable_openclaw",
    "cli_runtime_passthrough_openclaw",
    "auto_plugin",
    "auto_openclaw",
]


class AgentHarnessSelectionDecision(TypedDict):
    harness: Any
    policy: AgentHarnessPolicy
    selectedHarnessId: str
    selectedReason: SelectedReason
    candidates: list[AgentHarnessSelectionCandidate]


def _normalize_optional_agent_runtime_id(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = str(value).strip()
    return trimmed or None


def _is_default_agent_runtime_id(value: str | None) -> bool:
    return value is None or value.strip().lower() in ("", "default", "auto")


def _is_cli_runtime_alias_for_provider(*, runtime: str, provider: str, cfg: Any = None) -> bool:
    try:
        from openclaw.agents.model_runtime_aliases import is_cli_runtime_alias_for_provider

        return is_cli_runtime_alias_for_provider(runtime=runtime, provider=provider, cfg=cfg)
    except Exception:
        return False


def _list_plugin_agent_harnesses() -> list[Any]:
    return [entry["harness"] for entry in list_registered_agent_harnesses()]


def _list_harness_candidates(harnesses: list[Any]) -> list[AgentHarnessSelectionCandidate]:
    return [
        AgentHarnessSelectionCandidate(
            id=getattr(h, "id", ""),
            label=getattr(h, "label", ""),
            pluginId=getattr(h, "pluginId", None),
        )
        for h in harnesses
    ]


def _to_selection_candidate(entry: dict[str, Any]) -> AgentHarnessSelectionCandidate:
    harness = entry["harness"]
    support = entry["support"]
    candidate: AgentHarnessSelectionCandidate = AgentHarnessSelectionCandidate(
        id=getattr(harness, "id", ""),
        label=getattr(harness, "label", ""),
        pluginId=getattr(harness, "pluginId", None),
    )
    if isinstance(support, dict):
        candidate["supported"] = support.get("supported", False)
        if support.get("supported"):
            candidate["priority"] = support.get("priority", 0)
        if support.get("reason"):
            candidate["reason"] = support["reason"]
    return candidate


def _compare_harness_support(left: dict[str, Any], right: dict[str, Any]) -> int:
    left_priority = (left["support"].get("priority") or 0) if isinstance(left.get("support"), dict) else 0
    right_priority = (right["support"].get("priority") or 0) if isinstance(right.get("support"), dict) else 0
    delta = right_priority - left_priority
    if delta != 0:
        return delta
    left_id = getattr(left["harness"], "id", "")
    right_id = getattr(right["harness"], "id", "")
    return (left_id > right_id) - (left_id < right_id)


def _build_selection_decision(
    *,
    harness: Any,
    policy: AgentHarnessPolicy,
    selected_reason: SelectedReason,
    candidates: list[AgentHarnessSelectionCandidate],
) -> AgentHarnessSelectionDecision:
    return AgentHarnessSelectionDecision(
        harness=harness,
        policy=policy,
        selectedHarnessId=getattr(harness, "id", ""),
        selectedReason=selected_reason,
        candidates=candidates,
    )


def _format_provider_model(params: dict[str, Any]) -> str:
    provider = params.get("provider", "")
    model_id = params.get("modelId")
    return f"{provider}/{model_id}" if model_id else provider


def resolve_available_agent_harness_policy(params: dict[str, Any]) -> AgentHarnessPolicy:
    """Resolve harness policy with availability fallback."""
    return _apply_agent_harness_availability_policy(
        resolve_configured_agent_harness_policy(
            provider=params.get("provider"),
            model_id=params.get("modelId") or params.get("model_id"),
            config=params.get("config"),
            agent_id=params.get("agentId") or params.get("agent_id"),
            session_key=params.get("sessionKey") or params.get("session_key"),
            env=params.get("env"),
        )
    )


def _apply_agent_harness_availability_policy(policy: AgentHarnessPolicy) -> AgentHarnessPolicy:
    if (
        policy.get("runtime") == "codex"
        and policy.get("runtimeSource") == "implicit"
        and get_registered_agent_harness("codex") is None
    ):
        return {**policy, "runtime": "openclaw"}
    return policy


def select_agent_harness(params: dict[str, Any]) -> Any:
    """Select the appropriate agent harness for the given run parameters."""
    return _select_agent_harness_decision(params)["harness"]


def _select_agent_harness_decision(params: dict[str, Any]) -> AgentHarnessSelectionDecision:
    resolved_policy = resolve_configured_agent_harness_policy(
        provider=params.get("provider"),
        model_id=params.get("modelId") or params.get("model_id"),
        config=params.get("config"),
        agent_id=params.get("agentId") or params.get("agent_id"),
        session_key=params.get("sessionKey") or params.get("session_key"),
    )
    runtime_override = _normalize_optional_agent_runtime_id(params.get("agentHarnessRuntimeOverride"))
    if runtime_override and not _is_default_agent_runtime_id(runtime_override):
        policy: AgentHarnessPolicy = {
            **resolved_policy,
            "runtime": runtime_override,
            "runtimeSource": "model",
        }
    else:
        policy = resolved_policy

    plugin_harnesses = _list_plugin_agent_harnesses()
    openclaw_harness = create_openclaw_agent_harness()
    runtime = policy.get("runtime", "auto")

    if runtime == "openclaw":
        return _build_selection_decision(
            harness=openclaw_harness,
            policy=policy,
            selected_reason="forced_openclaw",
            candidates=_list_harness_candidates(plugin_harnesses),
        )

    if runtime != "auto":
        forced = next((h for h in plugin_harnesses if getattr(h, "id", "") == runtime), None)
        if forced is not None:
            support = forced.supports(
                {"provider": params.get("provider", ""), "modelId": params.get("modelId"), "requestedRuntime": runtime}
            )
            if isinstance(support, dict) and support.get("supported"):
                return _build_selection_decision(
                    harness=forced,
                    policy=policy,
                    selected_reason="forced_plugin",
                    candidates=_list_harness_candidates(plugin_harnesses),
                )
            if _is_cli_runtime_alias_for_provider(runtime=runtime, provider=params.get("provider", "")):
                return _build_selection_decision(
                    harness=openclaw_harness,
                    policy={**policy, "runtime": "openclaw"},
                    selected_reason="cli_runtime_passthrough_openclaw",
                    candidates=_list_harness_candidates(plugin_harnesses),
                )
            reason = support.get("reason") if isinstance(support, dict) else None
            suffix = f" ({reason})" if reason else ""
            raise ValueError(
                f'Requested agent harness "{runtime}" does not support {_format_provider_model(params)}{suffix}.'
            )
        if runtime == "codex" and policy.get("runtimeSource") == "implicit":
            return _build_selection_decision(
                harness=openclaw_harness,
                policy={**policy, "runtime": "openclaw"},
                selected_reason="implicit_plugin_unavailable_openclaw",
                candidates=_list_harness_candidates(plugin_harnesses),
            )
        if _is_cli_runtime_alias_for_provider(
            runtime=runtime, provider=params.get("provider", ""), cfg=params.get("config")
        ):
            return _build_selection_decision(
                harness=openclaw_harness,
                policy={**policy, "runtime": "openclaw"},
                selected_reason="cli_runtime_passthrough_openclaw",
                candidates=_list_harness_candidates(plugin_harnesses),
            )
        raise MissingAgentHarnessError(runtime)

    candidates = [
        {
            "harness": h,
            "support": h.supports(
                {"provider": params.get("provider", ""), "modelId": params.get("modelId"), "requestedRuntime": "auto"}
            ),
        }
        for h in plugin_harnesses
    ]
    supported = sorted(
        [c for c in candidates if isinstance(c["support"], dict) and c["support"].get("supported")],
        key=cmp_to_key(_compare_harness_support),
    )
    if supported:
        selected = supported[0]["harness"]
        return _build_selection_decision(
            harness=selected,
            policy=policy,
            selected_reason="auto_plugin",
            candidates=[_to_selection_candidate(c) for c in candidates],
        )
    return _build_selection_decision(
        harness=openclaw_harness,
        policy=policy,
        selected_reason="auto_openclaw",
        candidates=[_to_selection_candidate(c) for c in candidates],
    )


async def run_agent_harness_attempt(params: dict[str, Any]) -> dict[str, Any]:
    """Select and run a harness attempt, applying deny-all tool policy for plugin harnesses."""
    selection = _select_agent_harness_decision(
        {
            "provider": params.get("provider"),
            "modelId": params.get("modelId"),
            "config": params.get("config"),
            "agentId": params.get("agentId"),
            "sessionKey": params.get("sessionKey"),
            "agentHarnessId": params.get("agentHarnessId"),
            "agentHarnessRuntimeOverride": params.get("agentHarnessRuntimeOverride"),
        }
    )
    harness = selection["harness"]
    attempt_params = (
        params if getattr(harness, "id", "") == "openclaw" else _apply_plugin_harness_deny_all_tool_policy(params)
    )
    return await run_agent_harness_lifecycle_attempt(harness, attempt_params)


def _apply_plugin_harness_deny_all_tool_policy(params: dict[str, Any]) -> dict[str, Any]:
    prompt = _resolve_plugin_harness_deny_all_tool_policy_prompt(params)
    if not prompt:
        return params
    return {
        **params,
        "toolsAllow": [],
        "extraSystemPrompt": _append_plugin_harness_tool_policy_prompt(params.get("extraSystemPrompt"), prompt),
    }


def _append_plugin_harness_tool_policy_prompt(existing: str | None, prompt: str) -> str:
    trimmed = (existing or "").strip()
    if not trimmed:
        return prompt
    if prompt in trimmed:
        return trimmed
    return f"{trimmed}\n\n{prompt}"


def _resolve_plugin_harness_deny_all_tool_policy_prompt(params: dict[str, Any]) -> str | None:
    # The full tool-policy resolution requires many unported modules.
    # This stub returns None so plugin harness params pass through unchanged
    # until the policy stack is available.
    del params
    return None


def resolve_plugin_harness_policy_tools_allow(params: dict[str, Any]) -> list[str] | None:
    """Return ``[]`` when tool policy restricts native tools, else ``None``."""
    # Deferred: full tool-policy stack needed.
    del params
    return None
