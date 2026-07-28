from __future__ import annotations

from typing import Any


class ContextPruningStrategy:
    AUTO = "auto"
    AGGRESSIVE = "aggressive"
    CONSERVATIVE = "conservative"
    DISABLED = "disabled"


class ContextPruningTrigger:
    TOKEN_THRESHOLD = "token_threshold"
    TURN_COUNT = "turn_count"
    TIME_WINDOW = "time_window"


def resolve_context_pruning_policy(
    strategy: str = ContextPruningStrategy.AUTO,
    max_tokens: int = 128000,
    trigger_tokens: int = 100000,
) -> dict[str, Any]:
    if strategy == ContextPruningStrategy.DISABLED:
        return {"enabled": False, "strategy": strategy}

    return {
        "enabled": True,
        "strategy": strategy,
        "maxTokens": max_tokens,
        "triggerTokens": trigger_tokens,
        "safetyMarginTokens": 20000,
    }


def should_prune_context(
    current_tokens: int,
    policy: dict[str, Any] | None = None,
) -> bool:
    if not policy or not policy.get("enabled"):
        return False
    trigger = policy.get("triggerTokens", 100000)
    return current_tokens >= trigger
