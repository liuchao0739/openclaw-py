"""Agent harness lifecycle diagnostics wrapper.

This module wraps harness attempts with context-engine support checks,
diagnostic events, trace propagation, and result classification.

Diagnostic/trace infrastructure is resolved lazily; when unavailable the
lifecycle still runs the harness attempt and applies result classification.
"""

from __future__ import annotations

import time
from typing import Any, Literal

from openclaw.agents.harness.result_classification import (
    apply_agent_harness_result_classification,
)


def _get_active_diagnostic_trace_context() -> Any | None:
    try:
        from openclaw.infra.diagnostic_trace_context import get_active_diagnostic_trace_context
    except Exception:
        return None
    return get_active_diagnostic_trace_context()


def _run_with_diagnostic_trace_context(trace: Any, fn: Any) -> Any:
    try:
        from openclaw.infra.diagnostic_trace_context import run_with_diagnostic_trace_context
    except Exception:
        return fn()
    return run_with_diagnostic_trace_context(trace, fn)


def _emit_trusted_diagnostic_event(event: dict[str, Any]) -> None:
    try:
        from openclaw.infra.diagnostic_events import emit_trusted_diagnostic_event

        emit_trusted_diagnostic_event(event)
    except Exception:
        pass


def _diagnostic_error_category(error: Any) -> str | None:
    try:
        from openclaw.infra.diagnostic_error_metadata import diagnostic_error_category

        return diagnostic_error_category(error)
    except Exception:
        return None


def _diagnostic_channel(params: dict[str, Any]) -> str | None:
    return params.get("messageChannel") or params.get("messageProvider")


def _agent_harness_diagnostic_base(
    harness: Any,
    params: dict[str, Any],
    trace: Any | None = None,
) -> dict[str, Any]:
    diagnostic_trace = trace if trace is not None else _get_active_diagnostic_trace_context()
    channel = _diagnostic_channel(params)
    base: dict[str, Any] = {
        "runId": params.get("runId"),
        "sessionId": params.get("sessionId"),
        "provider": params.get("provider"),
        "model": params.get("modelId"),
        "harnessId": getattr(harness, "id", None),
    }
    plugin_id = getattr(harness, "pluginId", None)
    if plugin_id:
        base["pluginId"] = plugin_id
    if params.get("sessionKey"):
        base["sessionKey"] = params["sessionKey"]
    if params.get("trigger"):
        base["trigger"] = params["trigger"]
    if channel:
        base["channel"] = channel
    if diagnostic_trace is not None:
        base["trace"] = diagnostic_trace
    return base


def _agent_harness_run_outcome(result: dict[str, Any]) -> str:
    if result.get("promptError"):
        return "error"
    if result.get("externalAbort") or result.get("aborted"):
        return "aborted"
    if (
        result.get("timedOut")
        or result.get("idleTimedOut")
        or result.get("timedOutDuringCompaction")
    ):
        return "timed_out"
    return "completed"


def _should_emit_agent_run_diagnostics(harness: Any) -> bool:
    return getattr(harness, "id", None) != "openclaw"


def _agent_run_completion(result: dict[str, Any]) -> dict[str, Any]:
    if result.get("promptErrorSource") == "hook:before_agent_run":
        return {"outcome": "blocked", "blockedBy": "before_agent_run"}
    if result.get("promptError"):
        return {"outcome": "error", "error": result["promptError"]}
    if (
        result.get("externalAbort")
        or result.get("aborted")
        or result.get("timedOut")
        or result.get("idleTimedOut")
        or result.get("timedOutDuringCompaction")
    ):
        return {"outcome": "aborted"}
    return {"outcome": "completed"}


async def run_agent_harness_lifecycle_attempt(
    harness: Any,
    params: dict[str, Any],
) -> dict[str, Any]:
    """Run one harness attempt with diagnostics, tracing, and result classification."""
    started_at = int(time.time() * 1000)
    active_harness_trace = _get_active_diagnostic_trace_context()

    _emit_trusted_diagnostic_event(
        {"type": "harness.run.started", **_agent_harness_diagnostic_base(harness, params, active_harness_trace)}
    )

    phase = "prepare"
    try:
        phase = "send"
        raw_result = await harness.run_attempt(params)
        phase = "resolve"
        result = apply_agent_harness_result_classification(harness, raw_result, params)
    except Exception as error:
        _emit_trusted_diagnostic_event(
            {
                "type": "harness.run.error",
                **_agent_harness_diagnostic_base(harness, params, active_harness_trace),
                "durationMs": int(time.time() * 1000) - started_at,
                "phase": phase,
                "errorCategory": _diagnostic_error_category(error),
            }
        )
        raise

    _emit_trusted_diagnostic_event(
        {
            "type": "harness.run.completed",
            **_agent_harness_diagnostic_base(harness, params, active_harness_trace),
            "durationMs": int(time.time() * 1000) - started_at,
            "outcome": _agent_harness_run_outcome(result),
            **(
                {"resultClassification": result["agentHarnessResultClassification"]}
                if result.get("agentHarnessResultClassification")
                else {}
            ),
            **(
                {"yieldDetected": result["yieldDetected"]}
                if isinstance(result.get("yieldDetected"), bool)
                else {}
            ),
        }
    )
    return result
