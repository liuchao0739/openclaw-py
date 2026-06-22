"""Estimates reducible tool-result character budget for preemptive compaction."""

from __future__ import annotations

import json
import math
from typing import Any, TypedDict

DEFAULT_MAX_LIVE_TOOL_RESULT_CHARS = 16_000
LARGE_CONTEXT_MAX_LIVE_TOOL_RESULT_CHARS = 32_000
XL_CONTEXT_MAX_LIVE_TOOL_RESULT_CHARS = 64_000
LARGE_CONTEXT_TOOL_RESULT_TOKENS = 100_000
XL_CONTEXT_TOOL_RESULT_TOKENS = 200_000
MAX_TOOL_RESULT_CONTEXT_SHARE = 0.3


class ToolResultReductionPotential(TypedDict):
    maxChars: int
    aggregateBudgetChars: int
    toolResultCount: int
    totalToolResultChars: int
    oversizedCount: int
    oversizedReducibleChars: int
    aggregateReducibleChars: int
    maxReducibleChars: int


def _resolve_auto_live_tool_result_max_chars(context_window_tokens: int) -> int:
    if not math.isfinite(context_window_tokens):
        return DEFAULT_MAX_LIVE_TOOL_RESULT_CHARS
    tokens = int(context_window_tokens)
    if tokens >= XL_CONTEXT_TOOL_RESULT_TOKENS:
        return XL_CONTEXT_MAX_LIVE_TOOL_RESULT_CHARS
    if tokens >= LARGE_CONTEXT_TOOL_RESULT_TOKENS:
        return LARGE_CONTEXT_MAX_LIVE_TOOL_RESULT_CHARS
    return DEFAULT_MAX_LIVE_TOOL_RESULT_CHARS


def calculate_max_tool_result_chars(context_window_tokens: int) -> int:
    hard_cap = _resolve_auto_live_tool_result_max_chars(context_window_tokens)
    max_tokens = int(context_window_tokens * MAX_TOOL_RESULT_CONTEXT_SHARE)
    max_chars = max_tokens * 4
    return min(max_chars, max(1, hard_cap))


def get_tool_result_text_length(msg: dict[str, Any]) -> int:
    if msg.get("role") != "toolResult":
        return 0
    content = msg.get("content")
    if not isinstance(content, list):
        return 0
    total = 0
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            text = block.get("text")
            if isinstance(text, str):
                total += len(text)
    return total


def estimate_tool_result_reduction_potential(
    *,
    messages: list[dict[str, Any]],
    context_window_tokens: int,
    max_chars_override: int | None = None,
    aggregate_max_chars_override: int | None = None,
) -> ToolResultReductionPotential:
    max_chars = max(
        1,
        max_chars_override if max_chars_override is not None else calculate_max_tool_result_chars(context_window_tokens),
    )
    aggregate_budget_chars = max_chars * 8
    if aggregate_max_chars_override is not None:
        aggregate_budget_chars = max(1, aggregate_max_chars_override)

    tool_result_count = 0
    total_tool_result_chars = 0
    oversized_reducible = 0
    oversized_count = 0

    for msg in messages:
        if msg.get("role") != "toolResult":
            continue
        text_length = get_tool_result_text_length(msg)
        if text_length <= 0:
            continue
        tool_result_count += 1
        total_tool_result_chars += text_length
        if text_length > max_chars:
            oversized_count += 1
            oversized_reducible += text_length - max_chars

    aggregate_reducible = 0
    if total_tool_result_chars > aggregate_budget_chars:
        aggregate_reducible = total_tool_result_chars - aggregate_budget_chars

    max_reducible = oversized_reducible + aggregate_reducible

    return {
        "maxChars": max_chars,
        "aggregateBudgetChars": aggregate_budget_chars,
        "toolResultCount": tool_result_count,
        "totalToolResultChars": total_tool_result_chars,
        "oversizedCount": oversized_count,
        "oversizedReducibleChars": oversized_reducible,
        "aggregateReducibleChars": aggregate_reducible,
        "maxReducibleChars": max_reducible,
    }