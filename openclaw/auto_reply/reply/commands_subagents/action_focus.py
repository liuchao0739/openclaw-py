"""Focus action — focus on a specific subagent."""

from __future__ import annotations

from typing import Any

from openclaw.auto_reply.reply.commands_subagents.shared import (
    stop_with_text,
    stop_with_unknown_target_error,
)


def handle_focus_action(
    params: dict[str, Any],
    runs: list[dict[str, Any]],
    rest_tokens: list[str],
) -> dict[str, Any]:
    """Handle the /focus command to focus on a subagent."""
    from openclaw.auto_reply.reply.commands_subagents.shared import resolve_subagent_target

    if not rest_tokens:
        return stop_with_text("Usage: /focus <subagent-id|index|label>")

    token = rest_tokens[0]
    result = resolve_subagent_target(runs, token)

    if "error" in result:
        return stop_with_unknown_target_error(result["error"])

    entry = result["entry"]
    from openclaw.auto_reply.reply.commands_subagents.shared import format_run_label

    label = format_run_label(entry)
    return stop_with_text(f"🎯 Focused on subagent: {label}")
