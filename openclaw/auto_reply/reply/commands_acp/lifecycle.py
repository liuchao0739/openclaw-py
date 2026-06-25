"""ACP lifecycle management for command replies."""

from __future__ import annotations

from typing import Any, Literal

AcpLifecyclePhase = Literal["init", "ready", "running", "stopping", "stopped", "error"]


def get_acp_lifecycle_phase(session_meta: dict[str, Any] | None) -> AcpLifecyclePhase:
    """Get the lifecycle phase from ACP session metadata."""
    if not session_meta:
        return "stopped"
    return session_meta.get("lifecyclePhase", "stopped")


def is_acp_session_active(session_meta: dict[str, Any] | None) -> bool:
    """Check if an ACP session is in an active lifecycle phase."""
    phase = get_acp_lifecycle_phase(session_meta)
    return phase in ("ready", "running")


def is_acp_session_starting(session_meta: dict[str, Any] | None) -> bool:
    """Check if an ACP session is starting."""
    phase = get_acp_lifecycle_phase(session_meta)
    return phase == "init"


def format_lifecycle_status(session_meta: dict[str, Any] | None) -> str:
    """Format the lifecycle status for display."""
    phase = get_acp_lifecycle_phase(session_meta)
    session_id = session_meta.get("sessionId", "unknown") if session_meta else "none"
    return f"ACP session {session_id}: {phase}"
