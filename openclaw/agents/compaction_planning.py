from __future__ import annotations

from typing import Any


def run_computation(
    messages: list[dict[str, Any]],
    max_tokens: int = 128000,
    trigger_tokens: int = 100000,
) -> dict[str, Any]:
    total_input = sum(len(str(m.get("content", ""))) for m in messages)
    should_compact = total_input >= trigger_tokens
    return {
        "shouldCompact": should_compact,
        "totalInputTokens": total_input,
        "messageCount": len(messages),
        "maxTokens": max_tokens,
    }


def plan_compaction(
    messages: list[dict[str, Any]],
    max_tokens: int = 128000,
) -> dict[str, Any]:
    return {
        "strategy": "summarize",
        "keepSystemPrompt": True,
        "summarizeMessages": True,
        "truncateMessages": False,
    }
