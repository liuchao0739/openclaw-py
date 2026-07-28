from __future__ import annotations

from typing import Any


def build_tool_error_summary(
    errors: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "errors": errors or [],
        "count": len(errors or []),
        "hasErrors": bool(errors),
    }


def summarize_tool_errors(
    errors: list[dict[str, Any]],
) -> str:
    if not errors:
        return ""
    messages = [e.get("message", str(e)) for e in errors[:5]]
    return "; ".join(messages)
