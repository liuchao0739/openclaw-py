"""Info action — display detailed info for a subagent."""

from __future__ import annotations

from typing import Any

from openclaw.auto_reply.reply.commands_subagents.shared import (
    format_run_label,
    resolve_subagent_target,
    stop_with_text,
    stop_with_unknown_target_error,
)


def handle_info_action(
    params: dict[str, Any],
    runs: list[dict[str, Any]],
    rest_tokens: list[str],
) -> dict[str, Any]:
    """Handle the /subagents info command."""
    if not rest_tokens:
        return stop_with_text("Usage: /subagents info <subagent-id|index|label>")

    token = rest_tokens[0]
    result = resolve_subagent_target(runs, token)

    if "error" in result:
        return stop_with_unknown_target_error(result["error"])

    entry = result["entry"]
    lines: list[str] = ["ℹ️ Subagent Info:", ""]

    fields = [
        ("Run ID", entry.get("runId", "—")),
        ("Session ID", entry.get("sessionId", "—")),
        ("Task", entry.get("taskName", "—")),
        ("Status", entry.get("status", "unknown")),
        ("Agent", entry.get("agentId", "—")),
        ("Provider", entry.get("provider", "—")),
        ("Model", entry.get("model", "—")),
        ("Started", str(entry.get("startedAt", "—"))),
    ]

    if entry.get("endedAt"):
        fields.append(("Ended", str(entry["endedAt"])))

    for label, value in fields:
        lines.append(f"  {label}: {value}")

    return stop_with_text("\n".join(lines))
