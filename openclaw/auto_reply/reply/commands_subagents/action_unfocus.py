"""Unfocus action — remove focus from a subagent."""

from __future__ import annotations

from typing import Any

from openclaw.auto_reply.reply.commands_subagents.shared import stop_with_text


def handle_unfocus_action(
    params: dict[str, Any],
    runs: list[dict[str, Any]],
    rest_tokens: list[str],
) -> dict[str, Any]:
    """Handle the /unfocus command to remove subagent focus."""
    return stop_with_text("🔍 Unfocused from subagent. Now viewing main session.")
