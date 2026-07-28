from __future__ import annotations

import json
from typing import Any

from openclaw.llm.core import Message

from ...agent_types import AgentMessage
from ..harness_types import FileOperations

TOOL_RESULT_MAX_CHARS = 2000


def create_file_ops() -> FileOperations:
    return FileOperations()


def extract_file_ops_from_message(
    message: AgentMessage,
    file_ops: FileOperations,
) -> None:
    if message.get("role") != "assistant":
        return
    content = message.get("content")
    if not isinstance(content, list):
        return
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") != "toolCall":
            continue
        if "arguments" not in block or "name" not in block:
            continue
        args = block.get("arguments")
        if not args:
            continue
        path = args.get("path") if isinstance(args, dict) else None
        if not path or not isinstance(path, str):
            continue
        name = block.get("name")
        if name == "read":
            file_ops.read.add(path)
        elif name == "write":
            file_ops.written.add(path)
        elif name == "edit":
            file_ops.edited.add(path)


def compute_file_lists(
    file_ops: FileOperations,
) -> tuple[list[str], list[str]]:
    modified = set(file_ops.edited) | set(file_ops.written)
    read_only = sorted(f for f in file_ops.read if f not in modified)
    modified_files = sorted(modified)
    return read_only, modified_files


def format_file_operations(read_files: list[str], modified_files: list[str]) -> str:
    sections: list[str] = []
    if read_files:
        sections.append(f"<read-files>\n{chr(10).join(read_files)}\n</read-files>")
    if modified_files:
        sections.append(f"<modified-files>\n{chr(10).join(modified_files)}\n</modified-files>")
    if not sections:
        return ""
    return f"\n\n{chr(10).join(sections)}"


def _safe_json_stringify(value: Any) -> str:
    try:
        return json.dumps(value) if value is not None else "undefined"
    except (TypeError, ValueError):
        return "[unserializable]"


def _truncate_for_summary(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    truncated = len(text) - max_chars
    return f"{text[:max_chars]}\n\n[... {truncated} more characters truncated]"


def serialize_conversation(messages: list[Message]) -> str:
    parts: list[str] = []
    for msg in messages:
        role = msg.get("role") if isinstance(msg, dict) else getattr(msg, "role", None)
        if role == "user":
            content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", None)
            if isinstance(content, str):
                text = content
            elif isinstance(content, list):
                text = "".join(
                    c.get("text", "") if isinstance(c, dict) else getattr(c, "text", "")
                    for c in content
                    if (c.get("type") if isinstance(c, dict) else getattr(c, "type", None)) == "text"
                )
            else:
                text = ""
            if text:
                parts.append(f"[User]: {text}")
        elif role == "assistant":
            text_parts: list[str] = []
            thinking_parts: list[str] = []
            tool_calls: list[str] = []
            content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", None)
            if isinstance(content, list):
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    btype = block.get("type")
                    if btype == "text":
                        text_parts.append(block.get("text", ""))
                    elif btype == "thinking":
                        thinking_parts.append(block.get("thinking", ""))
                    elif btype == "toolCall":
                        args = block.get("arguments", {})
                        if isinstance(args, dict):
                            args_str = ", ".join(
                                f"{k}={_safe_json_stringify(v)}" for k, v in args.items()
                            )
                        else:
                            args_str = _safe_json_stringify(args)
                        tool_calls.append(f"{block.get('name')}({args_str})")
            if thinking_parts:
                parts.append(f"[Assistant thinking]: {chr(10).join(thinking_parts)}")
            if text_parts:
                parts.append(f"[Assistant]: {chr(10).join(text_parts)}")
            if tool_calls:
                parts.append(f"[Assistant tool calls]: {'; '.join(tool_calls)}")
        elif role == "toolResult":
            content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", None)
            if isinstance(content, list):
                text = "".join(
                    c.get("text", "") if isinstance(c, dict) else getattr(c, "text", "")
                    for c in content
                    if (c.get("type") if isinstance(c, dict) else getattr(c, "type", None)) == "text"
                )
            else:
                text = ""
            if text:
                parts.append(
                    f"[Tool result]: {_truncate_for_summary(text, TOOL_RESULT_MAX_CHARS)}"
                )
    return "\n\n".join(parts)
