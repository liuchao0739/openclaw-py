"""Provider failure classification helpers (partial)."""

from __future__ import annotations

GENERIC_ASSISTANT_ERROR_TEXT = "LLM request failed."


def is_reasoning_constraint_error_message(raw: str) -> bool:
    if not raw:
        return False
    lower = raw.strip().lower()
    return (
        "reasoning is mandatory" in lower
        or "reasoning is required" in lower
        or "requires reasoning" in lower
        or ("reasoning" in lower and "cannot be disabled" in lower)
    )