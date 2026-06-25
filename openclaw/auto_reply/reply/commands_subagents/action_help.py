"""Help action — display subagent command help."""

from __future__ import annotations

from typing import Any

from openclaw.auto_reply.reply.commands_subagents.shared import stop_with_text

_HELP_TEXT = """Subagent Commands:
  /subagents list     — List active and recent subagent runs
  /subagents log <id> — Show log for a specific subagent
  /subagents info <id>— Show detailed info for a subagent
  /subagents help     — Show this help message
  /focus <id>         — Focus on a specific subagent's output
  /unfocus            — Return focus to the main session
  /agents             — List registered agent harnesses

The <id> can be a run id (prefix), session id, index from the list, or task label."""


def handle_help_action(
    params: dict[str, Any],
    runs: list[dict[str, Any]],
    rest_tokens: list[str],
) -> dict[str, Any]:
    """Handle the /subagents help command."""
    return stop_with_text(_HELP_TEXT)
