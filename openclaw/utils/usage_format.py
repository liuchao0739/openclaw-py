from __future__ import annotations

import math
from typing import Any

from openclaw.utils.token_format import format_token_count


def format_usd(value: float | None) -> str | None:
    if value is None or not math.isfinite(value):
        return None
    if value >= 0.01:
        return f"${value:.2f}"
    return f"${value:.4f}"


def _to_number(value: Any) -> float:
    if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
        return value
    return 0


def estimate_usage_cost(params: dict) -> float | None:
    usage = params.get("usage")
    cost = params.get("cost")
    if not usage or not cost:
        return None
    input_tokens = _to_number(usage.get("input"))
    output_tokens = _to_number(usage.get("output"))
    cache_read = _to_number(usage.get("cacheRead"))
    cache_write = _to_number(usage.get("cacheWrite"))

    tiered_pricing = cost.get("tieredPricing")
    if tiered_pricing:
        total = _compute_tiered_cost(tiered_pricing, input_tokens, output_tokens, cache_read, cache_write)
    else:
        total = (
            input_tokens * cost.get("input", 0)
            + output_tokens * cost.get("output", 0)
            + cache_read * cost.get("cacheRead", 0)
            + cache_write * cost.get("cacheWrite", 0)
        )

    if not math.isfinite(total):
        return None
    return total / 1_000_000


def _select_pricing_tier(tiers: list, input_tokens: float) -> dict | None:
    sorted_tiers = sorted(tiers, key=lambda t: t["range"][0])
    if not sorted_tiers:
        return None
    if input_tokens <= 0:
        return sorted_tiers[0]
    for tier in sorted_tiers:
        start, end = tier["range"]
        if start <= input_tokens < end:
            return tier
    for tier in reversed(sorted_tiers):
        if input_tokens >= tier["range"][0]:
            return tier
    return sorted_tiers[0]


def _compute_tiered_cost(
    tiers: list, input_tokens: float, output_tokens: float, cache_read: float, cache_write: float
) -> float:
    tier = _select_pricing_tier(tiers, input_tokens)
    if not tier:
        return 0
    return (
        input_tokens * tier["input"]
        + output_tokens * tier["output"]
        + cache_read * tier["cacheRead"]
        + cache_write * tier["cacheWrite"]
    )


def resolve_model_cost_config(params: dict) -> dict | None:
    return None


def resolve_model_cost_config_fingerprint(config: Any = None) -> str:
    return ""


def reset_usage_format_caches_for_test() -> None:
    pass
