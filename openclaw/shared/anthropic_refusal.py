"""Anthropic refusal helpers for formatting provider refusal messages."""

from __future__ import annotations

import time
from typing import Any


def _read_nullable_string(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _read_anthropic_refusal_details(value: Any) -> tuple[str | None, str | None]:
    if not isinstance(value, dict):
        return (None, None)
    category = _read_nullable_string(value.get("category"))
    explanation = _read_nullable_string(value.get("explanation"))
    return (category, explanation)


def _format_anthropic_refusal_message(category: str | None, explanation: str | None) -> str:
    cat = f" (category: {category})" if category else ""
    expl = f": {explanation}" if explanation else "."
    return f"Anthropic refusal{cat}{expl}"


def apply_anthropic_refusal(
    output: dict[str, Any],
    stop_details: Any,
    provider: str,
) -> None:
    category, explanation = _read_anthropic_refusal_details(stop_details)
    output["stopReason"] = "error"
    output["errorMessage"] = _format_anthropic_refusal_message(category, explanation)
    diagnostics = output.get("diagnostics", [])
    if not isinstance(diagnostics, list):
        diagnostics = []
    diagnostics.append({
        "type": "provider_refusal",
        "timestamp": int(time.time() * 1000),
        "details": {
            "provider": provider,
            "category": category,
            "explanation": explanation,
        },
    })
    output["diagnostics"] = diagnostics
