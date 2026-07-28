from __future__ import annotations

from typing import Any


def build_context_window_guard(
    max_tokens: int = 128000,
    trigger_tokens: int = 100000,
    safety_margin: int = 20000,
) -> dict[str, Any]:
    return {
        "maxTokens": max_tokens,
        "triggerTokens": trigger_tokens,
        "safetyMargin": safety_margin,
        "active": False,
    }


def evaluate_context_window(
    current_tokens: int,
    guard: dict[str, Any] | None = None,
) -> dict[str, Any]:
    guard = guard or build_context_window_guard()
    result = {
        "safe": True,
        "currentTokens": current_tokens,
        "maxTokens": guard.get("maxTokens", 128000),
    }

    trigger = guard.get("triggerTokens", 100000)
    if current_tokens >= trigger:
        result["safe"] = False
        result["warning"] = True

    max_tok = guard.get("maxTokens", 128000)
    if current_tokens >= max_tok:
        result["safe"] = False
        result["critical"] = True

    return result
