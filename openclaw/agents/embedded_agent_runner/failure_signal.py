"""Converts embedded run failures into provider failover signals."""

from __future__ import annotations

from openclaw.agents.embedded_agent_runner.types import EmbeddedRunFailureSignal
from openclaw.agents.tool_error_summary import ToolErrorSummary, is_exec_like_tool_name

_FAILURE_SIGNAL_CODES = frozenset({"SYSTEM_RUN_DENIED", "INVALID_REQUEST"})


def _normalize_optional_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    s = value.strip()
    return s or None


def _resolve_failure_signal_code(value: str | None) -> str | None:
    if value in _FAILURE_SIGNAL_CODES:
        return value
    return None


def resolve_embedded_run_failure_signal(
    *,
    trigger: str | None = None,
    last_tool_error: ToolErrorSummary | None = None,
) -> EmbeddedRunFailureSignal | None:
    if trigger != "cron":
        return None
    if not last_tool_error or not is_exec_like_tool_name(last_tool_error.get("toolName")):
        return None
    code = _resolve_failure_signal_code(_normalize_optional_string(last_tool_error.get("errorCode")))
    if not code:
        return None
    message = _normalize_optional_string(last_tool_error.get("error")) or code
    out: EmbeddedRunFailureSignal = {
        "kind": "execution_denied",
        "source": "tool",
        "code": code,  # type: ignore[typeddict-item]
        "message": message,
        "fatalForCron": True,
    }
    tool_name = last_tool_error.get("toolName")
    if tool_name:
        out["toolName"] = tool_name
    return out