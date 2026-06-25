"""Compaction token math and thresholds (agent-core harness/compaction/compaction.ts)."""

from __future__ import annotations

import json
from typing import Any, TypedDict


class CompactionSettings(TypedDict):
    enabled: bool
    reserveTokens: int
    keepRecentTokens: int


DEFAULT_COMPACTION_SETTINGS: CompactionSettings = {
    "enabled": True,
    "reserveTokens": 16384,
    "keepRecentTokens": 20000,
}


class ContextUsageEstimate(TypedDict):
    tokens: int
    usageTokens: int
    trailingTokens: int
    lastUsageIndex: int | None


class Usage(TypedDict, total=False):
    totalTokens: int
    input: int
    output: int
    cacheRead: int
    cacheWrite: int


def calculate_context_tokens(usage: Usage) -> int:
    total = usage.get("totalTokens")
    if total:
        return int(total)
    return int(
        usage.get("input", 0)
        + usage.get("output", 0)
        + usage.get("cacheRead", 0)
        + usage.get("cacheWrite", 0)
    )


def _get_assistant_usage(msg: dict[str, Any]) -> Usage | None:
    if msg.get("role") != "assistant":
        return None
    stop = msg.get("stopReason")
    if stop in ("aborted", "error"):
        return None
    usage = msg.get("usage")
    if isinstance(usage, dict):
        return usage  # type: ignore[return-value]
    return None


def get_last_assistant_usage(entries: list[dict[str, Any]]) -> Usage | None:
    for entry in reversed(entries):
        if entry.get("type") != "message":
            continue
        message = entry.get("message")
        if not isinstance(message, dict):
            continue
        usage = _get_assistant_usage(message)
        if usage:
            return usage
    return None


def _safe_json_stringify(value: Any) -> str:
    try:
        return json.dumps(value)
    except (TypeError, ValueError):
        return "[unserializable]"


def estimate_tokens(message: dict[str, Any]) -> int:
    role = message.get("role")
    chars = 0
    if role == "user":
        content = message.get("content")
        if isinstance(content, str):
            chars = len(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text = block.get("text")
                    if isinstance(text, str):
                        chars += len(text)
    elif role == "assistant":
        content = message.get("content")
        if isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                btype = block.get("type")
                if btype == "text" and isinstance(block.get("text"), str):
                    chars += len(block["text"])
                elif btype == "thinking" and isinstance(block.get("thinking"), str):
                    chars += len(block["thinking"])
                elif btype == "toolCall":
                    name = block.get("name")
                    if isinstance(name, str):
                        chars += len(name)
                    chars += len(_safe_json_stringify(block.get("arguments")))
    elif role in ("custom", "toolResult", "tool"):
        content = message.get("content")
        if isinstance(content, str):
            chars = len(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text = block.get("text")
                    if isinstance(text, str):
                        chars += len(text)
                if isinstance(block, dict) and block.get("type") == "image":
                    chars += 4800
    elif role == "bashExecution":
        cmd = message.get("command")
        out = message.get("output")
        if isinstance(cmd, str):
            chars += len(cmd)
        if isinstance(out, str):
            chars += len(out)
    elif role in ("branchSummary", "compactionSummary"):
        summary = message.get("summary")
        if isinstance(summary, str):
            chars = len(summary)
    return (chars + 3) // 4 if chars else 0


def _last_assistant_usage_info(messages: list[dict[str, Any]]) -> tuple[Usage, int] | None:
    for i in range(len(messages) - 1, -1, -1):
        usage = _get_assistant_usage(messages[i])
        if usage:
            return usage, i
    return None


def estimate_context_tokens(messages: list[dict[str, Any]]) -> ContextUsageEstimate:
    info = _last_assistant_usage_info(messages)
    if not info:
        estimated = sum(estimate_tokens(m) for m in messages)
        return {
            "tokens": estimated,
            "usageTokens": 0,
            "trailingTokens": estimated,
            "lastUsageIndex": None,
        }
    usage, index = info
    usage_tokens = calculate_context_tokens(usage)
    trailing = sum(estimate_tokens(messages[j]) for j in range(index + 1, len(messages)))
    return {
        "tokens": usage_tokens + trailing,
        "usageTokens": usage_tokens,
        "trailingTokens": trailing,
        "lastUsageIndex": index,
    }


def should_compact(
    context_tokens: int,
    context_window: int,
    settings: CompactionSettings,
) -> bool:
    if not settings.get("enabled", True):
        return False
    reserve = int(settings.get("reserveTokens", DEFAULT_COMPACTION_SETTINGS["reserveTokens"]))
    return context_tokens > context_window - reserve