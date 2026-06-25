"""Agent harness lifecycle hook helpers.

This module dispatches LLM/agent lifecycle plugin hooks and normalizes
before-finalize retry/finalize decisions with bounded retry accounting.
"""

from __future__ import annotations

import hashlib
from typing import Any, Literal, TypedDict


def _normalize_optional_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    trimmed = value.strip()
    return trimmed or None


def _get_global_hook_runner() -> Any | None:
    try:
        from openclaw.plugins.hook_runner_global import get_global_hook_runner
    except Exception:
        return None
    return get_global_hook_runner()


def _resolve_global_singleton(key: str, factory: Any) -> Any:
    import sys

    if not hasattr(sys, "_openclaw_singletons"):
        sys._openclaw_singletons = {}  # type: ignore[attr-defined]
    singletons = sys._openclaw_singletons  # type: ignore[attr-defined]
    if key not in singletons:
        singletons[key] = factory()
    return singletons[key]


_FINALIZE_RETRY_BUDGET_KEY = "openclaw.pluginFinalizeRetryBudget"
_FINALIZE_RETRY_BUDGET_MAX_ENTRIES = 2048


def get_agent_harness_hook_runner() -> Any | None:
    """Return the current global hook runner for harness lifecycle hooks."""
    return _get_global_hook_runner()


def _get_finalize_retry_budget() -> dict[str, dict[str, int]]:
    return _resolve_global_singleton(
        _FINALIZE_RETRY_BUDGET_KEY, lambda: {}
    )


def _count_finalize_retry_budget_entries(budget: dict[str, dict[str, int]]) -> int:
    return sum(len(v) for v in budget.values())


def _prune_finalize_retry_budget(budget: dict[str, dict[str, int]]) -> None:
    while _count_finalize_retry_budget_entries(budget) > _FINALIZE_RETRY_BUDGET_MAX_ENTRIES:
        if not budget:
            return
        oldest_run_id = next(iter(budget))
        oldest_run_budget = budget[oldest_run_id]
        if not oldest_run_budget:
            budget.pop(oldest_run_id)
            continue
        oldest_retry_key = next(iter(oldest_run_budget))
        oldest_run_budget.pop(oldest_retry_key, None)
        if not oldest_run_budget:
            budget.pop(oldest_run_id, None)


def _build_finalize_retry_instruction_key(instruction: str) -> str:
    return f"instruction:{hashlib.sha256(instruction.encode('utf-8')).hexdigest()}"


def clear_agent_harness_finalize_retry_budget(params: dict[str, Any] | None = None) -> None:
    """Clear before-finalize retry budgets globally or for one run."""
    budget = _get_finalize_retry_budget()
    if not params or not params.get("runId"):
        budget.clear()
        return
    budget.pop(params["runId"], None)


def run_agent_harness_llm_input_hook(params: dict[str, Any]) -> None:
    """Dispatch best-effort LLM input hooks for a harness attempt."""
    hook_runner = params.get("hookRunner") or _get_global_hook_runner()
    if hook_runner is None or not hook_runner.has_hooks("llm_input"):
        return
    run_llm_input = getattr(hook_runner, "run_llm_input", None)
    if run_llm_input is None:
        return
    from openclaw.agents.harness.hook_context import build_agent_hook_context

    import asyncio

    async def _fire() -> None:
        try:
            await run_llm_input(params["event"], build_agent_hook_context(params["ctx"]))
        except Exception:
            pass

    try:
        loop = asyncio.get_event_loop()
        loop.create_task(_fire())
    except Exception:
        pass


def run_agent_harness_llm_output_hook(params: dict[str, Any]) -> None:
    """Dispatch best-effort LLM output hooks for a harness attempt."""
    hook_runner = params.get("hookRunner") or _get_global_hook_runner()
    if hook_runner is None or not hook_runner.has_hooks("llm_output"):
        return
    run_llm_output = getattr(hook_runner, "run_llm_output", None)
    if run_llm_output is None:
        return
    from openclaw.agents.harness.hook_context import build_agent_hook_context

    import asyncio

    async def _fire() -> None:
        try:
            await run_llm_output(params["event"], build_agent_hook_context(params["ctx"]))
        except Exception:
            pass

    try:
        loop = asyncio.get_event_loop()
        loop.create_task(_fire())
    except Exception:
        pass


class AgentHarnessBeforeAgentFinalizeOutcome(TypedDict, total=False):
    action: Literal["continue", "revise", "finalize"]
    reason: str


async def _execute_agent_end_hook(params: dict[str, Any], *, unref_timeout: bool) -> None:
    hook_runner = params.get("hookRunner") or _get_global_hook_runner()
    if hook_runner is None or not hook_runner.has_hooks("agent_end"):
        return
    run_agent_end = getattr(hook_runner, "run_agent_end", None)
    if run_agent_end is None:
        return
    from openclaw.agents.harness.hook_context import build_agent_hook_context

    try:
        await run_agent_end(
            params["event"],
            build_agent_hook_context(params["ctx"]),
            {"unrefTimeout": unref_timeout},
        )
    except Exception:
        pass


def run_agent_harness_agent_end_hook(params: dict[str, Any]) -> None:
    """Start agent_end hooks with unref timeout behavior."""
    import asyncio

    def _fire() -> None:
        try:
            loop = asyncio.get_event_loop()
            loop.create_task(_execute_agent_end_hook({**params, "unrefTimeout": True}, unref_timeout=True))
        except Exception:
            pass

    _fire()


async def await_agent_harness_agent_end_hook(params: dict[str, Any]) -> None:
    """Run agent_end hooks and wait for completion."""
    await _execute_agent_end_hook(params, unref_timeout=False)


async def run_agent_harness_before_agent_finalize_hook(
    params: dict[str, Any],
) -> AgentHarnessBeforeAgentFinalizeOutcome:
    """Run before-finalize hooks and normalize finalize/revise/continue decisions."""
    hook_runner = params.get("hookRunner") or _get_global_hook_runner()
    if hook_runner is None or not hook_runner.has_hooks("before_agent_finalize"):
        return {"action": "continue"}
    run_before_agent_finalize = getattr(hook_runner, "run_before_agent_finalize", None)
    if run_before_agent_finalize is None:
        return {"action": "continue"}
    from openclaw.agents.harness.hook_context import build_agent_hook_context

    event = {**params["event"], "runId": params["event"].get("runId") or params["ctx"].get("runId")}
    try:
        result = await run_before_agent_finalize(event, build_agent_hook_context(params["ctx"]))
        return _normalize_before_agent_finalize_result(result, event)
    except Exception:
        return {"action": "continue"}


def _normalize_before_agent_finalize_result(
    result: dict[str, Any] | None,
    event: dict[str, Any] | None = None,
) -> AgentHarnessBeforeAgentFinalizeOutcome:
    if result is not None and result.get("action") == "finalize":
        reason = _normalize_optional_string(result.get("reason"))
        if reason:
            return {"action": "finalize", "reason": reason}
        return {"action": "finalize"}
    if result is not None and result.get("action") == "revise":
        retry_candidates = _read_before_agent_finalize_retry_candidates(result)
        if retry_candidates:
            reason = _normalize_optional_string(result.get("reason"))
            for retry in retry_candidates:
                retry_instruction = _normalize_optional_string(retry.get("instruction"))
                if not retry_instruction:
                    continue
                max_attempts_raw = retry.get("maxAttempts")
                max_attempts = (
                    max(1, int(max_attempts_raw))
                    if isinstance(max_attempts_raw, (int, float)) and max_attempts_raw == max_attempts_raw
                    else 1
                )
                retry_run_id = (event or {}).get("runId") or (event or {}).get("sessionId") or "unknown-run"
                retry_key = _normalize_optional_string(retry.get("idempotencyKey")) or _build_finalize_retry_instruction_key(
                    retry_instruction
                )
                budget = _get_finalize_retry_budget()
                run_budget = budget.get(retry_run_id, {})
                next_count = run_budget.get(retry_key, 0) + 1
                run_budget.pop(retry_key, None)
                run_budget[retry_key] = next_count
                budget.pop(retry_run_id, None)
                budget[retry_run_id] = run_budget
                _prune_finalize_retry_budget(budget)
                if next_count > max_attempts:
                    continue
                revised_reason = (
                    reason
                    if reason and retry_instruction in reason
                    else "\n\n".join([x for x in [reason, retry_instruction] if x])
                )
                return {"action": "revise", "reason": revised_reason}
            return {"action": "continue"}
        reason = _normalize_optional_string(result.get("reason"))
        if reason:
            return {"action": "revise", "reason": reason}
        return {"action": "continue"}
    return {"action": "continue"}


def _read_before_agent_finalize_retry_candidates(result: dict[str, Any]) -> list[dict[str, Any]]:
    candidate_list = result.get("retryCandidates")
    if isinstance(candidate_list, list) and candidate_list:
        return [c for c in candidate_list if _is_before_agent_finalize_retry(c)]
    retry = result.get("retry")
    return [retry] if _is_before_agent_finalize_retry(retry) else []


def _is_before_agent_finalize_retry(value: Any) -> bool:
    return bool(value) and isinstance(value, dict) and not isinstance(value, list)
