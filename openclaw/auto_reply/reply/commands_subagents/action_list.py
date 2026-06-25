"""List action — list active and recent subagent runs."""

from __future__ import annotations

from typing import Any

from openclaw.auto_reply.reply.commands_subagents.shared import (
    format_run_label,
    is_active_run,
    is_recent_run,
    stop_with_text,
)


def handle_list_action(
    params: dict[str, Any],
    runs: list[dict[str, Any]],
    rest_tokens: list[str],
) -> dict[str, Any]:
    """Handle the /subagents list command."""
    if not runs:
        return stop_with_text("No subagent runs found.")

    lines: list[str] = ["📋 Subagent Runs:", ""]

    active_runs = [r for r in runs if is_active_run(r)]
    recent_runs = [r for r in runs if not is_active_run(r) and is_recent_run(r)]

    if active_runs:
        lines.append("Active:")
        for i, entry in enumerate(active_runs, 1):
            lines.append(f"  {i}. {format_run_label(entry)}")
        lines.append("")

    if recent_runs:
        lines.append("Recent:")
        for i, entry in enumerate(recent_runs, 1):
            lines.append(f"  {i}. {format_run_label(entry)}")
        lines.append("")

    if not active_runs and not recent_runs:
        lines.append("No active or recent runs.")

    return stop_with_text("\n".join(lines))
