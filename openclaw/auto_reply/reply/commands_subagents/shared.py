"""Shared helpers for subagent command actions and target resolution."""

from __future__ import annotations

from typing import Any

COMMAND = "/subagents"
COMMAND_FOCUS = "/focus"
COMMAND_UNFOCUS = "/unfocus"
COMMAND_AGENTS = "/agents"

ACTIONS = frozenset({"list", "log", "info", "help"})
RECENT_WINDOW_MINUTES = 30

SubagentsAction = str  # "list" | "log" | "info" | "focus" | "unfocus" | "agents" | "help"


def stop_with_text(text: str) -> dict[str, Any]:
    """Create a command handler result that stops with a text reply."""
    return {"shouldContinue": False, "reply": {"text": text}}


def stop_with_unknown_target_error(error: str | None = None) -> dict[str, Any]:
    """Create a command handler result for an unknown subagent target."""
    return stop_with_text(f"⚠️ {error or 'Unknown subagent.'}")


def resolve_subagent_target(
    runs: list[dict[str, Any]],
    token: str | None,
) -> dict[str, Any]:
    """Resolve a subagent target from runs and a token (id, index, or label)."""
    if not token:
        return {"error": "Missing subagent id."}

    token = token.strip()

    # Try index (e.g., "1", "2")
    try:
        index = int(token)
        if 1 <= index <= len(runs):
            return {"entry": runs[index - 1]}
        return {"error": f"Invalid subagent index: {token}"}
    except ValueError:
        pass

    # Try run id prefix match
    matches = [r for r in runs if r.get("runId", "").startswith(token)]
    if len(matches) == 1:
        return {"entry": matches[0]}
    if len(matches) > 1:
        return {"error": f"Ambiguous run id prefix: {token}"}

    # Try session id match
    matches = [r for r in runs if r.get("sessionId") == token]
    if len(matches) == 1:
        return {"entry": matches[0]}
    if len(matches) > 1:
        return {"error": f"Unknown subagent session: {token}"}

    # Try task name match
    matches = [r for r in runs if r.get("taskName") == token]
    if len(matches) == 1:
        return {"entry": matches[0]}
    if len(matches) > 1:
        return {"error": f"Ambiguous subagent label: {token}"}

    # Try task name prefix match
    matches = [r for r in runs if r.get("taskName", "").startswith(token)]
    if len(matches) == 1:
        return {"entry": matches[0]}
    if len(matches) > 1:
        return {"error": f"Ambiguous subagent label prefix: {token}"}

    return {"error": f"Unknown subagent id: {token}"}


def format_run_label(entry: dict[str, Any]) -> str:
    """Format a run label for display."""
    task_name = entry.get("taskName", "")
    run_id = entry.get("runId", "")[:8]
    status = entry.get("status", "unknown")
    if task_name:
        return f"{task_name} ({run_id}, {status})"
    return f"{run_id} ({status})"


def is_recent_run(entry: dict[str, Any], window_minutes: int = RECENT_WINDOW_MINUTES) -> bool:
    """Check if a run is within the recent window."""
    import time

    started_at = entry.get("startedAt")
    if not started_at:
        return False
    now = time.time() * 1000
    return (now - started_at) < (window_minutes * 60 * 1000)


def is_active_run(entry: dict[str, Any]) -> bool:
    """Check if a run is still active."""
    return not entry.get("endedAt")
