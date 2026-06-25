"""ACP diagnostics and runtime error formatting for command replies."""

from __future__ import annotations

from typing import Any


def format_acp_runtime_error_text(error: Any) -> str:
    """Format an ACP runtime error for display in command replies."""
    if isinstance(error, str):
        return error
    if isinstance(error, dict):
        message = error.get("message", "")
        code = error.get("code", "")
        if message and code:
            return f"[{code}] {message}"
        return message or str(error)
    if isinstance(error, Exception):
        return str(error)
    return str(error) if error else ""


def format_acp_session_diagnostics(entries: list[dict[str, Any]]) -> str:
    """Format ACP session entries for diagnostic display."""
    if not entries:
        return "No ACP sessions found."

    lines: list[str] = []
    for entry in entries:
        session_id = entry.get("sessionId", "unknown")
        status = entry.get("status", "unknown")
        agent_id = entry.get("agentId", "")
        provider = entry.get("provider", "")
        model = entry.get("model", "")

        parts = [f"[{status}] {session_id}"]
        if agent_id:
            parts.append(f"agent={agent_id}")
        if provider:
            parts.append(f"provider={provider}")
        if model:
            parts.append(f"model={model}")
        lines.append(" ".join(parts))

    return "\n".join(lines)


def to_acp_runtime_error(error: Any) -> dict[str, Any]:
    """Normalize an error into an ACP runtime error dict."""
    if isinstance(error, dict):
        return error
    if isinstance(error, Exception):
        return {"message": str(error), "code": type(error).__name__}
    return {"message": str(error) if error else "Unknown error", "code": "Unknown"}
