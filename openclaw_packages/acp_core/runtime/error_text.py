from __future__ import annotations

from typing import Any

from .errors import AcpRuntimeError


def _resolve_acp_runtime_error_next_step(error: AcpRuntimeError) -> str | None:
    if error.code in ("ACP_BACKEND_MISSING", "ACP_BACKEND_UNAVAILABLE"):
        return "Run `/acp doctor`, install/enable the backend plugin, then retry."
    if error.code == "ACP_DISPATCH_DISABLED":
        return "Enable `acp.dispatch.enabled=true` to allow thread-message ACP turns."
    if error.code == "ACP_SESSION_INIT_FAILED":
        return "If this session is stale, recreate it with `/acp spawn` and rebind the thread."
    if error.code == "ACP_INVALID_RUNTIME_OPTION":
        return "Use `/acp status` to inspect options and pass valid values."
    if error.code == "ACP_BACKEND_UNSUPPORTED_CONTROL":
        return "This backend does not support that control; use a supported command."
    if error.code == "ACP_TURN_FAILED":
        return "Retry, or use `/acp cancel` and send the message again."
    return None


def format_acp_runtime_error_text(error: AcpRuntimeError) -> str:
    next_step = _resolve_acp_runtime_error_next_step(error)
    if not next_step:
        return f"ACP error ({error.code}): {str(error)}"
    return f"ACP error ({error.code}): {str(error)}\nnext: {next_step}"


def to_acp_runtime_error_text(
    error: Any,
    fallback_code: str,
    fallback_message: str,
) -> str:
    from .errors import to_acp_runtime_error

    return format_acp_runtime_error_text(
        to_acp_runtime_error(error, fallback_code, fallback_message)
    )