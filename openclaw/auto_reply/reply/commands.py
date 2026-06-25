"""Main chat command router for auto-reply command turns.

This module re-exports the command context builder and handler.
The full implementations are deferred until the command processing layer is ported.
"""

from __future__ import annotations

from typing import Any


def build_command_context(params: dict[str, Any]) -> dict[str, Any]:
    """Build command context from handler params.

    Deferred to commands_context module; this stub returns a minimal context.
    """
    return {
        "command": params.get("command", {}),
        "ctx": params.get("ctx", {}),
        "cfg": params.get("cfg", {}),
        "body": params.get("body", ""),
    }


def build_status_reply(params: dict[str, Any]) -> dict[str, Any]:
    """Build a status reply for /status command.

    Deferred to commands_status module; this stub returns a basic reply.
    """
    return {
        "shouldContinue": False,
        "reply": {"text": "Status: OK"},
    }
