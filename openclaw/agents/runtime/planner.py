from __future__ import annotations

from typing import Any


def resolve_runtime_plan(
    messages: list[dict[str, Any]],
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "steps": [],
        "totalTokens": 0,
        "messageCount": len(messages),
    }


def should_compact_context(
    messages: list[dict[str, Any]],
    trigger_tokens: int = 100000,
) -> bool:
    total = sum(len(str(m.get("content", ""))) for m in messages)
    return total >= trigger_tokens
