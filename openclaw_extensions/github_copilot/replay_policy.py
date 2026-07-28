from __future__ import annotations

from typing import Any

from openclaw.plugin_sdk.string_coerce_runtime import normalize_lowercase_string_or_empty

OMITTED_COPILOT_REASONING_TEXT = "[assistant reasoning omitted]"


def _is_copilot_claude_model(model_id: str | None) -> bool:
    return "claude" in normalize_lowercase_string_or_empty(model_id)


def _is_thinking_block(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    block_type = value.get("type")
    return block_type == "thinking" or block_type == "redacted_thinking"


def strip_copilot_assistant_thinking_messages(messages: list[Any]) -> list[Any]:
    touched = False
    sanitized = []
    for message in messages:
        if not isinstance(message, dict):
            sanitized.append(message)
            continue
        record = message
        if record.get("role") != "assistant" or not isinstance(record.get("content"), list):
            sanitized.append(message)
            continue
        content = [block for block in record["content"] if not _is_thinking_block(block)]
        if len(content) == len(record["content"]):
            sanitized.append(message)
            continue
        touched = True
        new_msg = dict(message)
        new_msg["content"] = content if content else [{"type": "text", "text": OMITTED_COPILOT_REASONING_TEXT}]
        sanitized.append(new_msg)
    return sanitized if touched else messages


def build_github_copilot_replay_policy(model_id: str | None = None) -> dict[str, Any]:
    if _is_copilot_claude_model(model_id):
        return {"dropThinkingBlocks": True}
    return {}


def sanitize_github_copilot_replay_history(ctx: dict[str, Any]) -> list[Any]:
    if _is_copilot_claude_model(ctx.get("modelId")):
        return strip_copilot_assistant_thinking_messages(ctx.get("messages", []))
    return ctx.get("messages", [])
