"""Shared error helpers for model-list availability fallback behavior."""

from __future__ import annotations

from typing import Any

MODEL_AVAILABILITY_UNAVAILABLE_CODE = "MODEL_AVAILABILITY_UNAVAILABLE"


def format_error_with_stack(err: Any) -> str:
    """Format an unknown error with stack detail when available."""
    if isinstance(err, Exception):
        return f"{type(err).__name__}: {err}"
    return str(err)


def should_fallback_to_auth_heuristics(err: Any) -> bool:
    """Return True when model list should continue with auth heuristics."""
    if not isinstance(err, Exception):
        return False
    code = getattr(err, "code", None)
    return code == MODEL_AVAILABILITY_UNAVAILABLE_CODE
