"""Subagent formatting helpers for durations and token counts."""

from __future__ import annotations

import math
from typing import Any


def format_token_short(value: int | float | None) -> str | None:
    if value is None or not math.isfinite(value) or value <= 0:
        return None
    n = int(value)
    if n < 1000:
        return str(n)
    if n < 10000:
        return f"{n / 1000:.1f}".rstrip("0").rstrip(".") + "k"
    if n < 1000000:
        thousands = round(n / 1000)
        if thousands < 1000:
            return f"{thousands}k"
    return f"{n / 1000000:.1f}".rstrip("0").rstrip(".") + "m"


def truncate_line(value: str, max_length: int) -> str:
    if len(value) <= max_length:
        return value
    return f"{value[:max_length].rstrip()}..."


def resolve_total_tokens(entry: dict[str, Any] | None = None) -> int | None:
    if not isinstance(entry, dict):
        return None
    total = entry.get("totalTokens")
    if isinstance(total, (int, float)) and math.isfinite(total):
        return int(total)
    input_tokens = entry.get("inputTokens", 0)
    output_tokens = entry.get("outputTokens", 0)
    input_val = input_tokens if isinstance(input_tokens, (int, float)) else 0
    output_val = output_tokens if isinstance(output_tokens, (int, float)) else 0
    total_val = input_val + output_val
    return total_val if total_val > 0 else None


def resolve_io_tokens(entry: dict[str, Any] | None = None) -> dict[str, int] | None:
    if not isinstance(entry, dict):
        return None
    input_tokens = entry.get("inputTokens", 0)
    output_tokens = entry.get("outputTokens", 0)
    input_val = input_tokens if isinstance(input_tokens, (int, float)) and math.isfinite(input_tokens) else 0
    output_val = output_tokens if isinstance(output_tokens, (int, float)) and math.isfinite(output_tokens) else 0
    total = input_val + output_val
    if total <= 0:
        return None
    return {"input": input_val, "output": output_val, "total": total}


def format_token_usage_display(entry: dict[str, Any] | None = None) -> str:
    io = resolve_io_tokens(entry)
    prompt_cache = resolve_total_tokens(entry)
    parts: list[str] = []
    if io:
        input_str = format_token_short(io["input"]) or "0"
        output_str = format_token_short(io["output"]) or "0"
        total_str = format_token_short(io["total"]) or "0"
        parts.append(f"tokens {total_str} (in {input_str} / out {output_str})")
    elif isinstance(prompt_cache, int) and prompt_cache > 0:
        parts.append(f"tokens {format_token_short(prompt_cache)} prompt/cache")
    if isinstance(prompt_cache, int) and io and prompt_cache > io["total"]:
        parts.append(f"prompt/cache {format_token_short(prompt_cache)}")
    return ", ".join(parts)
