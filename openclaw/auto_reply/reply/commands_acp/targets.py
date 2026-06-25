"""ACP target resolution for command replies."""

from __future__ import annotations

from typing import Any


def resolve_acp_target(params: dict[str, Any]) -> dict[str, Any]:
    """Resolve the ACP target from command params."""
    command = params.get("command", {})
    ctx = params.get("ctx", {})

    target: dict[str, Any] = {
        "channel": (command.get("channel") or ctx.get("channel") or "").strip(),
        "agentId": command.get("agentId") or ctx.get("agentId"),
    }

    # Resolve session key
    session_key = ctx.get("sessionKey")
    if session_key:
        target["sessionKey"] = session_key

    # Resolve session ID
    session_id = ctx.get("sessionId")
    if session_id:
        target["sessionId"] = session_id

    # Resolve workspace dir
    workspace_dir = ctx.get("workspaceDir")
    if workspace_dir:
        target["workspaceDir"] = workspace_dir

    return target


def is_valid_acp_target(target: dict[str, Any]) -> bool:
    """Check if an ACP target has the required fields."""
    return bool(target.get("channel"))


def format_acp_target_display(target: dict[str, Any]) -> str:
    """Format an ACP target for display."""
    parts: list[str] = []
    channel = target.get("channel", "")
    agent_id = target.get("agentId", "")
    session_id = target.get("sessionId", "")

    if channel:
        parts.append(f"channel={channel}")
    if agent_id:
        parts.append(f"agent={agent_id}")
    if session_id:
        parts.append(f"session={session_id}")

    return ", ".join(parts) if parts else "default"
