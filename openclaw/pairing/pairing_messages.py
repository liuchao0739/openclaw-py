"""Formats pairing challenge replies and setup instructions.

Mirrors src/pairing/pairing-messages.ts.
"""

from __future__ import annotations


def _format_cli_command(command: str) -> str:
    """Format a CLI command for display. Simple passthrough."""
    return command


def build_pairing_reply(params: dict[str, str]) -> str:
    """Build a user-facing pairing reply sent to unapproved channel users.

    The owner command is formatted through CLI helpers so profiles/aliases stay valid.
    """
    channel = params["channel"]
    id_line = params["idLine"]
    code = params["code"]
    approve_command = _format_cli_command(f"openclaw pairing approve {channel} {code}")
    return "\n".join([
        "OpenClaw: access not configured.",
        "",
        id_line,
        "Pairing code:",
        "```",
        code,
        "```",
        "",
        "Ask the bot owner to approve with:",
        "```",
        approve_command,
        "```",
    ])
