"""Shared ACP command helpers."""

from __future__ import annotations

from typing import Any


def is_acp_command(command: dict[str, Any]) -> bool:
    """Check if a command is an ACP command."""
    return command.get("type") == "acp" or command.get("protocol") == "acp"


def get_acp_command_type(command: dict[str, Any]) -> str | None:
    """Get the ACP command sub-type."""
    return command.get("acpCommand") or command.get("subcommand")


def normalize_acp_command(command: dict[str, Any]) -> dict[str, Any]:
    """Normalize an ACP command into a standard shape."""
    normalized: dict[str, Any] = {
        "type": "acp",
        "channel": (command.get("channel") or "").strip(),
        "agentId": command.get("agentId"),
        "provider": command.get("provider"),
        "model": command.get("model"),
        "prompt": command.get("prompt", ""),
    }

    # Optional fields
    for key in ("conversationId", "parentConversationId", "timeoutMs", "maxTurns"):
        if command.get(key) is not None:
            normalized[key] = command[key]

    return normalized


def merge_acp_command_defaults(
    command: dict[str, Any],
    defaults: dict[str, Any],
) -> dict[str, Any]:
    """Merge defaults into an ACP command, with command taking priority."""
    result = {**defaults, **command}
    # Ensure type is always set
    result["type"] = "acp"
    return result
