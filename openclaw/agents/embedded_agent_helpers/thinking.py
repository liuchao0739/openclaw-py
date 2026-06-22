"""Thinking-level fallback helpers."""

from __future__ import annotations

import re
from typing import Literal

from openclaw.agents.embedded_agent_helpers.errors import is_reasoning_constraint_error_message

ThinkLevel = Literal["off", "minimal", "low", "medium", "high", "xhigh", "max"]


def _normalize_think_level(entry: str) -> ThinkLevel | None:
    key = entry.strip().lower()
    if key in ("off", "minimal", "low", "medium", "high", "xhigh", "max"):
        return key  # type: ignore[return-value]
    return None


def _extract_supported_values(raw: str) -> list[str]:
    match = re.search(r"supported values are:\s*([^\n.]+)", raw, re.I) or re.search(
        r"supported values:\s*([^\n.]+)", raw, re.I
    )
    if not match:
        return []
    fragment = match.group(1)
    quoted = [m.group(1).strip() for m in re.finditer(r"['\"]([^'\"]+)['\"]", fragment) if m.group(1)]
    if quoted:
        return [q for q in quoted if q]
    return [
        re.sub(r"^[^a-zA-Z]+|[^a-zA-Z]+$", "", part)
        for part in re.split(r",|\band\b", fragment, flags=re.I)
        if part.strip()
    ]


def pick_fallback_thinking_level(
    *,
    message: str | None = None,
    attempted: set[ThinkLevel] | None = None,
) -> ThinkLevel | None:
    attempted = attempted or set()
    raw = (message or "").strip()
    if not raw:
        return None
    if is_reasoning_constraint_error_message(raw) and "minimal" not in attempted:
        return "minimal"
    supported = _extract_supported_values(raw)
    if not supported:
        if re.search(r"not supported", raw, re.I) and "off" not in attempted:
            return "off"
        return None
    for entry in supported:
        normalized = _normalize_think_level(entry)
        if normalized and normalized not in attempted:
            return normalized
    return None


def _is_thinking_block(block: object) -> bool:
    if not isinstance(block, dict):
        return False
    return block.get("type") in ("thinking", "redacted_thinking")


def drop_thinking_blocks(messages: list) -> list:
    latest_assistant = -1
    for i in range(len(messages) - 1, -1, -1):
        msg = messages[i]
        if isinstance(msg, dict) and msg.get("role") == "assistant" and isinstance(msg.get("content"), list):
            latest_assistant = i
            break
    out: list = []
    for i, msg in enumerate(messages):
        if not isinstance(msg, dict) or msg.get("role") != "assistant" or not isinstance(msg.get("content"), list):
            out.append(msg)
            continue
        if i == latest_assistant:
            out.append(msg)
            continue
        new_content = [b for b in msg["content"] if not _is_thinking_block(b)]
        if len(new_content) == len(msg["content"]):
            out.append(msg)
        else:
            out.append({**msg, "content": new_content})
    return out