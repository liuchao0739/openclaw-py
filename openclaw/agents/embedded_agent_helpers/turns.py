"""Normalize conversation turn ordering for provider contracts (turns.ts parity)."""

from __future__ import annotations

from typing import Any, Callable, Literal

from openclaw.agents.tool_call_id import extract_tool_calls_from_assistant, extract_tool_result_id

AgentMessage = dict[str, Any]
Role = Literal["assistant", "user"]


def _opt_str(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    s = value.strip()
    return s or None


def _is_tool_call_block(block: dict[str, Any]) -> bool:
    t = block.get("type")
    return t in ("toolUse", "toolCall", "functionCall")


def _is_thinking_like_block(block: Any) -> bool:
    if not isinstance(block, dict):
        return False
    t = block.get("type")
    return t in ("thinking", "redacted_thinking")


def _is_aborted_assistant_turn(message: AgentMessage) -> bool:
    stop = message.get("stopReason")
    return stop in ("aborted", "error")


def _extract_tool_result_match_ids(record: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    for key in (
        "toolUseId",
        "toolCallId",
        "tool_use_id",
        "tool_call_id",
        "callId",
        "call_id",
    ):
        v = _opt_str(record.get(key))
        if v:
            ids.add(v)
    return ids


def _extract_tool_result_match_name(record: dict[str, Any]) -> str | None:
    return _opt_str(record.get("toolName")) or _opt_str(record.get("name"))


def _collect_any_tool_result_ids(message: AgentMessage) -> set[str]:
    ids: set[str] = set()
    role = message.get("role")
    if role == "toolResult":
        tid = extract_tool_result_id(message)
        if tid:
            ids.add(tid)
    elif role == "tool":
        ids.update(_extract_tool_result_match_ids(message))

    content = message.get("content")
    if isinstance(content, list):
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") not in ("toolResult", "tool"):
                continue
            ids.update(_extract_tool_result_match_ids(block))
    return ids


def _collect_trusted_tool_result_matches(message: AgentMessage) -> dict[str, set[str]]:
    matches: dict[str, set[str]] = {}
    role = message.get("role")

    def add_match(id_iter: set[str], tool_name: str | None) -> None:
        for i in id_iter:
            bucket = matches.setdefault(i, set())
            if tool_name:
                bucket.add(tool_name)

    if role == "toolResult":
        record = message
        id_set = set(_extract_tool_result_match_ids(record))
        tid = extract_tool_result_id(message)
        if tid:
            id_set.add(tid)
        add_match(id_set, _extract_tool_result_match_name(record))
    elif role == "tool":
        record = message
        add_match(_extract_tool_result_match_ids(record), _extract_tool_result_match_name(record))
    return matches


def _collect_future_tool_result_matches(
    messages: list[AgentMessage], start_index: int
) -> dict[str, set[str]]:
    matches: dict[str, set[str]] = {}
    for index in range(start_index + 1, len(messages)):
        candidate = messages[index]
        if not isinstance(candidate, dict):
            continue
        if candidate.get("role") == "assistant":
            break
        for i, tool_names in _collect_trusted_tool_result_matches(candidate).items():
            bucket = matches.setdefault(i, set())
            bucket.update(tool_names)
    return matches


def _collect_future_tool_result_ids(messages: list[AgentMessage], start_index: int) -> set[str]:
    ids: set[str] = set()
    for index in range(start_index + 1, len(messages)):
        candidate = messages[index]
        if not isinstance(candidate, dict):
            continue
        if candidate.get("role") == "assistant":
            break
        ids.update(_collect_any_tool_result_ids(candidate))
    return ids


def _strip_dangling_anthropic_tool_uses(messages: list[AgentMessage]) -> list[AgentMessage]:
    result: list[AgentMessage] = []
    for i, msg in enumerate(messages):
        if not isinstance(msg, dict):
            result.append(msg)
            continue
        if msg.get("role") != "assistant":
            result.append(msg)
            continue

        content = msg.get("content")
        original = content if isinstance(content, list) else []
        if not original:
            result.append(msg)
            continue
        if not extract_tool_calls_from_assistant(msg):
            result.append(msg)
            continue

        has_thinking = any(_is_thinking_like_block(b) for b in original if isinstance(b, dict))
        valid_matches = _collect_future_tool_result_matches(messages, i)
        valid_ids = _collect_future_tool_result_ids(messages, i)

        if has_thinking:
            all_resolvable = True
            for block in original:
                if not isinstance(block, dict) or not _is_tool_call_block(block):
                    continue
                block_id = _opt_str(block.get("id"))
                block_name = _opt_str(block.get("name"))
                if not block_id or not block_name:
                    all_resolvable = False
                    break
                matching = valid_matches.get(block_id)
                if not matching:
                    all_resolvable = False
                    break
                if matching and block_name not in matching:
                    all_resolvable = False
                    break
            if all_resolvable:
                result.append(msg)
            else:
                new_msg = dict(msg)
                new_msg["content"] = (
                    []
                    if _is_aborted_assistant_turn(msg)
                    else [{"type": "text", "text": "[tool calls omitted]"}]
                )
                result.append(new_msg)
            continue

        filtered = []
        for block in original:
            if not block:
                continue
            if not isinstance(block, dict):
                filtered.append(block)
                continue
            if not _is_tool_call_block(block):
                filtered.append(block)
                continue
            block_id = _opt_str(block.get("id"))
            if block_id and block_id in valid_ids:
                filtered.append(block)

        if len(filtered) == len(original):
            result.append(msg)
            continue
        if original and not filtered:
            new_msg = dict(msg)
            new_msg["content"] = (
                []
                if _is_aborted_assistant_turn(msg)
                else [{"type": "text", "text": "[tool calls omitted]"}]
            )
            result.append(new_msg)
        else:
            new_msg = dict(msg)
            new_msg["content"] = filtered
            result.append(new_msg)
    return result


def _validate_turns_with_consecutive_merge(
    *,
    messages: list[AgentMessage],
    role: Role,
    merge: Callable[[AgentMessage, AgentMessage], AgentMessage],
) -> list[AgentMessage]:
    if not messages:
        return messages
    result: list[AgentMessage] = []
    last_role: str | None = None
    for msg in messages:
        if not isinstance(msg, dict):
            result.append(msg)
            continue
        msg_role = msg.get("role")
        if not msg_role:
            result.append(msg)
            continue
        if msg_role == last_role == role and result:
            last_msg = result[-1]
            if isinstance(last_msg, dict):
                result[-1] = merge(last_msg, msg)
                continue
        result.append(msg)
        last_role = str(msg_role)
    return result


def _merge_consecutive_assistant_turns(
    previous: AgentMessage, current: AgentMessage
) -> AgentMessage:
    prev_c = previous.get("content")
    cur_c = current.get("content")
    merged = [
        *(prev_c if isinstance(prev_c, list) else []),
        *(cur_c if isinstance(cur_c, list) else []),
    ]
    out = dict(previous)
    out["content"] = merged
    if current.get("usage"):
        out["usage"] = current["usage"]
    if current.get("stopReason"):
        out["stopReason"] = current["stopReason"]
    if current.get("errorMessage"):
        out["errorMessage"] = current["errorMessage"]
    return out


def _normalize_user_content_for_merge(content: Any) -> list[dict[str, Any]]:
    if isinstance(content, list):
        return [b for b in content if isinstance(b, dict)]
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    return []


def merge_consecutive_user_turns(previous: AgentMessage, current: AgentMessage) -> AgentMessage:
    merged = [
        *_normalize_user_content_for_merge(previous.get("content")),
        *_normalize_user_content_for_merge(current.get("content")),
    ]
    out = dict(current)
    out["content"] = merged
    ts = current.get("timestamp") or previous.get("timestamp")
    if ts is not None:
        out["timestamp"] = ts
    return out


def validate_gemini_turns(messages: list[AgentMessage]) -> list[AgentMessage]:
    return _validate_turns_with_consecutive_merge(
        messages=messages,
        role="assistant",
        merge=_merge_consecutive_assistant_turns,
    )


def validate_anthropic_turns(messages: list[AgentMessage]) -> list[AgentMessage]:
    merged_assistant = _validate_turns_with_consecutive_merge(
        messages=messages,
        role="assistant",
        merge=_merge_consecutive_assistant_turns,
    )
    stripped = _strip_dangling_anthropic_tool_uses(merged_assistant)
    return _validate_turns_with_consecutive_merge(
        messages=stripped,
        role="user",
        merge=merge_consecutive_user_turns,
    )