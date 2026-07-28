"""Shared agent liveness predicates for blocked-run detection and normalization."""

from __future__ import annotations

from typing import Any, Literal, TypeVar

TStatus = TypeVar("TStatus")


def is_blocked_liveness_state(liveness_state: Any) -> bool:
    if not isinstance(liveness_state, str):
        return False
    return liveness_state.strip().lower() == "blocked"


def format_blocked_liveness_error(error: Any) -> str:
    if isinstance(error, str):
        message = error.strip()
        if message:
            return message
    return "Agent run blocked before producing a usable result."


def normalize_blocked_liveness_wait_status(
    status: str,
    liveness_state: Any = None,
    error: Any = None,
) -> dict[str, Any]:
    error_str = error.strip() if isinstance(error, str) else None
    if not is_blocked_liveness_state(liveness_state):
        result: dict[str, Any] = {"status": status}
        if error_str is not None:
            result["error"] = error_str
        return result
    return {"status": "error", "error": format_blocked_liveness_error(error_str)}
