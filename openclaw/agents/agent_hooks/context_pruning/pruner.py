"""Context-pruning planner that trims old assistant/tool content under token pressure."""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any, Callable, Protocol

from openclaw.agents.agent_hooks.context_pruning.settings import EffectiveContextPruningSettings
from openclaw.agents.agent_hooks.context_pruning.tools import make_tool_prunable_predicate
from openclaw.llm.core import (
    AssistantMessage,
    ImageContent,
    Message,
    Model,
    TextContent,
    ToolCall,
    ToolResultMessage,
    UserMessage,
)
from openclaw.utils.cjk_chars import CHARS_PER_TOKEN_ESTIMATE, estimate_string_chars

AgentMessage = Message | dict[str, Any]

IMAGE_CHAR_ESTIMATE = 8_000
PRUNED_CONTEXT_IMAGE_MARKER = "[image removed during context pruning]"


class ExtensionContextLike(Protocol):
    model: Model | None


def drop_thinking_blocks(messages: list[AgentMessage]) -> list[AgentMessage]:
    """Strip thinking blocks from assistant messages for size estimates."""
    out: list[AgentMessage] = []
    for msg in messages:
        if isinstance(msg, dict):
            if msg.get("role") != "assistant":
                out.append(msg)
                continue
            content = msg.get("content")
            if not isinstance(content, list):
                out.append(msg)
                continue
            filtered = [
                b
                for b in content
                if not (
                    isinstance(b, dict)
                    and b.get("type") in ("thinking", "redacted_thinking")
                )
            ]
            if len(filtered) == len(content):
                out.append(msg)
            else:
                out.append({**msg, "content": filtered})
            continue
        if not isinstance(msg, AssistantMessage):
            out.append(msg)
            continue
        out.append(msg)
    return out


def _as_text(text: str) -> TextContent:
    return TextContent(text=text)


def _role(msg: AgentMessage) -> str | None:
    if isinstance(msg, dict):
        r = msg.get("role")
        return r if isinstance(r, str) else None
    return msg.role


def _coerce_text_block(block: Any) -> str | None:
    if not block or not isinstance(block, dict):
        if isinstance(block, TextContent):
            return block.text
        return None
    if block.get("type") != "text":
        return None
    text = block.get("text")
    if isinstance(text, str):
        return text
    try:
        return json.dumps(block)
    except (TypeError, ValueError):
        return "[malformed text block]"


def _is_image_block(block: Any) -> bool:
    if isinstance(block, ImageContent):
        return True
    return bool(block) and isinstance(block, dict) and block.get("type") == "image"


def _tool_result_content(msg: ToolResultMessage | dict[str, Any]) -> list[Any]:
    if isinstance(msg, dict):
        c = msg.get("content")
        return c if isinstance(c, list) else []
    return list(msg.content)


def _collect_text_segments(content: list[Any]) -> list[str]:
    parts: list[str] = []
    for block in content:
        text = _coerce_text_block(block)
        if text is not None:
            parts.append(text)
    return parts


def _collect_prunable_tool_result_segments(content: list[Any]) -> list[str]:
    parts: list[str] = []
    for block in content:
        text = _coerce_text_block(block)
        if text is not None:
            parts.append(text)
            continue
        if _is_image_block(block):
            parts.append(PRUNED_CONTEXT_IMAGE_MARKER)
    return parts


def _estimate_joined_text_length(parts: list[str]) -> int:
    if not parts:
        return 0
    return sum(len(p) for p in parts) + max(0, len(parts) - 1)


def _take_head_from_joined_text(parts: list[str], max_chars: int) -> str:
    if max_chars <= 0 or not parts:
        return ""
    remaining = max_chars
    out = ""
    for i, p in enumerate(parts):
        if i > 0:
            out += "\n"
            remaining -= 1
            if remaining <= 0:
                break
        if len(p) <= remaining:
            out += p
            remaining -= len(p)
        else:
            out += p[:remaining]
            break
    return out


def _take_tail_from_joined_text(parts: list[str], max_chars: int) -> str:
    if max_chars <= 0 or not parts:
        return ""
    remaining = max_chars
    chunks: list[str] = []
    for i in range(len(parts) - 1, -1, -1):
        p = parts[i]
        if len(p) <= remaining:
            chunks.append(p)
            remaining -= len(p)
        else:
            chunks.append(p[len(p) - remaining :])
            break
        if remaining > 0 and i > 0:
            chunks.append("\n")
            remaining -= 1
    chunks.reverse()
    return "".join(chunks)


def _has_image_blocks(content: list[Any]) -> bool:
    return any(_is_image_block(b) for b in content)


def _estimate_text_and_image_chars(content: list[Any]) -> int:
    chars = 0
    for block in content:
        text = _coerce_text_block(block)
        if text is not None:
            chars += estimate_string_chars(text)
            continue
        if _is_image_block(block):
            chars += IMAGE_CHAR_ESTIMATE
    return chars


def _estimate_message_chars(message: AgentMessage) -> int:
    role = _role(message)
    if role == "user":
        if isinstance(message, UserMessage):
            if isinstance(message.content, str):
                return estimate_string_chars(message.content)
            return _estimate_text_and_image_chars(list(message.content))
        content = message.get("content") if isinstance(message, dict) else None
        if isinstance(content, str):
            return estimate_string_chars(content)
        if isinstance(content, list):
            return _estimate_text_and_image_chars(content)
        return 256

    if role == "assistant":
        chars = 0
        blocks: list[Any]
        if isinstance(message, AssistantMessage):
            blocks = list(message.content)
        elif isinstance(message, dict):
            blocks = message.get("content") if isinstance(message.get("content"), list) else []
        else:
            return 256
        for b in blocks:
            if isinstance(b, ToolCall):
                try:
                    chars += len(json.dumps(b.arguments))
                except (TypeError, ValueError):
                    chars += 128
                continue
            if isinstance(b, TextContent):
                chars += estimate_string_chars(b.text)
                continue
            if not isinstance(b, dict):
                continue
            btype = b.get("type")
            if btype == "text" and isinstance(b.get("text"), str):
                chars += estimate_string_chars(b["text"])
            if btype in ("thinking", "redacted_thinking"):
                thinking = b.get("thinking")
                if isinstance(thinking, str):
                    chars += estimate_string_chars(thinking)
                data = b.get("data")
                if btype == "redacted_thinking" and isinstance(data, str):
                    chars += estimate_string_chars(data)
                sig = b.get("thinkingSignature")
                if isinstance(sig, str):
                    chars += estimate_string_chars(sig)
            if btype == "toolCall":
                try:
                    chars += len(json.dumps(b.get("arguments") or {}))
                except (TypeError, ValueError):
                    chars += 128
        return chars

    if role == "toolResult":
        return _estimate_text_and_image_chars(_tool_result_content(message))

    return 256


def _find_assistant_cutoff_index(messages: list[AgentMessage], keep_last_assistants: int) -> int | None:
    if keep_last_assistants <= 0:
        return len(messages)
    remaining = keep_last_assistants
    for i in range(len(messages) - 1, -1, -1):
        if _role(messages[i]) != "assistant":
            continue
        remaining -= 1
        if remaining == 0:
            return i
    return None


def _find_first_user_index(messages: list[AgentMessage]) -> int | None:
    for i, msg in enumerate(messages):
        if _role(msg) == "user":
            return i
    return None


def _soft_trim_tool_result_message(
    msg: ToolResultMessage | dict[str, Any],
    settings: EffectiveContextPruningSettings,
) -> ToolResultMessage | dict[str, Any] | None:
    content = _tool_result_content(msg)
    has_images = _has_image_blocks(content)
    parts = _collect_prunable_tool_result_segments(content) if has_images else _collect_text_segments(content)
    raw_len = _estimate_joined_text_length(parts)
    st = settings.soft_trim
    if raw_len <= st.max_chars:
        if not has_images:
            return None
        trimmed_text = "\n".join(parts)
        if isinstance(msg, ToolResultMessage):
            return msg.model_copy(update={"content": [_as_text(trimmed_text)]})
        return {**msg, "content": [{"type": "text", "text": trimmed_text}]}

    head_chars = max(0, st.head_chars)
    tail_chars = max(0, st.tail_chars)
    if head_chars + tail_chars >= raw_len:
        if not has_images:
            return None
        trimmed_text = "\n".join(parts)
        if isinstance(msg, ToolResultMessage):
            return msg.model_copy(update={"content": [_as_text(trimmed_text)]})
        return {**msg, "content": [{"type": "text", "text": trimmed_text}]}

    head = _take_head_from_joined_text(parts, head_chars)
    tail = _take_tail_from_joined_text(parts, tail_chars)
    trimmed = f"{head}\n...\n{tail}"
    note = (
        f"\n\n[Tool result trimmed: kept first {head_chars} chars and "
        f"last {tail_chars} chars of {raw_len} chars.]"
    )
    new_content = [_as_text(trimmed + note)]
    if isinstance(msg, ToolResultMessage):
        return msg.model_copy(update={"content": new_content})
    return {**msg, "content": [{"type": "text", "text": trimmed + note}]}


def _get_tool_name(msg: AgentMessage) -> str:
    if isinstance(msg, ToolResultMessage):
        return msg.tool_name
    if isinstance(msg, dict):
        name = msg.get("toolName") or msg.get("tool_name")
        return name if isinstance(name, str) else ""
    return ""


def _message_at(messages: list[AgentMessage], index: int) -> AgentMessage | None:
    if 0 <= index < len(messages):
        return messages[index]
    return None


def prune_context_messages(
    *,
    messages: list[AgentMessage],
    settings: EffectiveContextPruningSettings,
    ctx: ExtensionContextLike,
    is_tool_prunable: Callable[[str], bool] | None = None,
    context_window_tokens_override: int | None = None,
    drop_thinking_blocks_for_estimate: bool = False,
) -> list[AgentMessage]:
    override = context_window_tokens_override
    if isinstance(override, (int, float)) and override > 0:
        context_window_tokens = int(override)
    else:
        context_window_tokens = ctx.model.context_window if ctx.model else None

    if not context_window_tokens or context_window_tokens <= 0:
        return messages

    char_window = context_window_tokens * CHARS_PER_TOKEN_ESTIMATE
    if char_window <= 0:
        return messages

    cutoff_index = _find_assistant_cutoff_index(messages, settings.keep_last_assistants)
    if cutoff_index is None:
        return messages

    first_user_index = _find_first_user_index(messages)
    prune_start_index = len(messages) if first_user_index is None else first_user_index

    tool_prunable = is_tool_prunable or make_tool_prunable_predicate(settings.tools)
    estimated_messages = (
        drop_thinking_blocks(messages) if drop_thinking_blocks_for_estimate else messages
    )

    total_chars = sum(_estimate_message_chars(m) for m in estimated_messages)
    ratio = total_chars / char_window
    if ratio < settings.soft_trim_ratio:
        return messages

    prunable_tool_indexes: list[int] = []
    next_messages: list[AgentMessage] | None = None

    for i in range(prune_start_index, cutoff_index):
        msg = _message_at(messages, i)
        if msg is None or _role(msg) != "toolResult":
            continue
        if not tool_prunable(_get_tool_name(msg)):
            continue
        prunable_tool_indexes.append(i)

        updated = _soft_trim_tool_result_message(msg, settings)
        if updated is None:
            continue

        before_chars = _estimate_message_chars(msg)
        after_chars = _estimate_message_chars(updated)
        total_chars += after_chars - before_chars
        if next_messages is None:
            next_messages = list(messages)
        next_messages[i] = updated

    output_after_soft_trim = next_messages if next_messages is not None else messages
    ratio = total_chars / char_window
    if ratio < settings.hard_clear_ratio:
        return output_after_soft_trim
    if not settings.hard_clear.enabled:
        return output_after_soft_trim

    prunable_tool_chars = 0
    for i in prunable_tool_indexes:
        msg = _message_at(output_after_soft_trim, i)
        if msg is None or _role(msg) != "toolResult":
            continue
        prunable_tool_chars += _estimate_message_chars(msg)
    if prunable_tool_chars < settings.min_prunable_tool_chars:
        return output_after_soft_trim

    for i in prunable_tool_indexes:
        if ratio < settings.hard_clear_ratio:
            break
        source = next_messages if next_messages is not None else messages
        msg = _message_at(source, i)
        if msg is None or _role(msg) != "toolResult":
            continue
        before_chars = _estimate_message_chars(msg)
        placeholder = settings.hard_clear.placeholder
        if isinstance(msg, ToolResultMessage):
            cleared: AgentMessage = msg.model_copy(update={"content": [_as_text(placeholder)]})
        else:
            cleared = {**msg, "content": [{"type": "text", "text": placeholder}]}
        if next_messages is None:
            next_messages = list(messages)
        next_messages[i] = cleared
        after_chars = _estimate_message_chars(cleared)
        total_chars += after_chars - before_chars
        ratio = total_chars / char_window

    return next_messages if next_messages is not None else messages