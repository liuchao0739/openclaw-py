"""Log action — display log for a subagent."""

from __future__ import annotations

from typing import Any

from openclaw.auto_reply.reply.commands_subagents.shared import (
    format_run_label,
    resolve_subagent_target,
    stop_with_text,
    stop_with_unknown_target_error,
)


def handle_log_action(
    params: dict[str, Any],
    runs: list[dict[str, Any]],
    rest_tokens: list[str],
) -> dict[str, Any]:
    """Handle the /subagents log command."""
    if not rest_tokens:
        return stop_with_text("Usage: /subagents log <subagent-id|index|label>")

    token = rest_tokens[0]
    result = resolve_subagent_target(runs, token)

    if "error" in result:
        return stop_with_unknown_target_error(result["error"])

    entry = result["entry"]
    log_lines = entry.get("logLines", [])
    label = format_run_label(entry)

    if not log_lines:
        return stop_with_text(f"📄 No log output for subagent: {label}")

    # Show the last N log lines
    max_lines = 50
    truncated = log_lines[-max_lines:] if len(log_lines) > max_lines else log_lines

    lines: list[str] = [f"📄 Log for {label}:", ""]
    if len(log_lines) > max_lines:
        lines.append(f"[{len(log_lines) - max_lines} earlier lines omitted]")
        lines.append("")

    lines.extend(truncated)
    return stop_with_text("\n".join(lines))
