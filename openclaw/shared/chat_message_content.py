"""Chat message content helpers extract user-visible text from mixed message parts."""

from __future__ import annotations

import json
from typing import Any, Literal

AssistantPhase = Literal["commentary", "final_answer"]


def _is_assistant_text_content_block_type(value: Any) -> bool:
    return value in ("text", "input_text", "output_text")


def _normalize_assistant_phase(value: Any) -> AssistantPhase | None:
    if value in ("commentary", "final_answer"):
        return value
    return None


def _read_string_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    return None


def extract_first_text_block(message: Any) -> str | None:
    if not isinstance(message, dict):
        return None
    content = message.get("content")
    inline = _read_string_value(content)
    if inline is not None:
        return inline
    if not isinstance(content, list) or len(content) == 0:
        return None
    first = content[0]
    if not isinstance(first, dict):
        return None
    return _read_string_value(first.get("text"))


def parse_assistant_text_signature(
    value: Any,
) -> dict[str, Any] | None:
    if not isinstance(value, str) or len(value.strip()) == 0:
        return None
    if not value.startswith("{"):
        return {"id": value}
    try:
        parsed = json.loads(value)
        if parsed.get("v") != 1:
            return None
        result: dict[str, Any] = {}
        if isinstance(parsed.get("id"), str):
            result["id"] = parsed["id"]
        phase = _normalize_assistant_phase(parsed.get("phase"))
        if phase:
            result["phase"] = phase
        return result
    except (json.JSONDecodeError, TypeError):
        return None


def resolve_assistant_message_phase(message: Any) -> AssistantPhase | None:
    if not isinstance(message, dict):
        return None
    entry = message
    direct_phase = _normalize_assistant_phase(entry.get("phase"))
    if direct_phase:
        return direct_phase
    content = entry.get("content")
    if not isinstance(content, list):
        return None
    explicit_phases: set[str] = set()
    for block in content:
        if not isinstance(block, dict):
            continue
        record = block
        if not _is_assistant_text_content_block_type(record.get("type")):
            continue
        sig = parse_assistant_text_signature(record.get("textSignature"))
        if sig and sig.get("phase"):
            explicit_phases.add(sig["phase"])
    return next(iter(explicit_phases)) if len(explicit_phases) == 1 else None


def resolve_assistant_event_phase(data: Any) -> AssistantPhase | None:
    if not isinstance(data, dict):
        return None
    record = data
    return (
        _normalize_assistant_phase(record.get("phase"))
        or resolve_assistant_message_phase(record.get("message"))
        or resolve_assistant_message_phase(record.get("partial"))
        or resolve_assistant_message_phase(record.get("item"))
        or resolve_assistant_message_phase(record)
    )


def extract_assistant_text_for_phase(
    message: Any,
    phase: AssistantPhase | None = None,
    sanitize_text: callable | None = None,
    join_with: str = "\n",
) -> str | None:
    if not isinstance(message, dict):
        return None
    entry = message
    message_phase = _normalize_assistant_phase(entry.get("phase"))

    def _should_include(resolved_phase: str | None) -> bool:
        if phase:
            return resolved_phase == phase
        return resolved_phase is None

    sanitize_fn = sanitize_text
    join_sep = join_with

    if isinstance(entry.get("text"), str):
        if not _should_include(message_phase):
            return None
        text = entry["text"]
        if sanitize_fn:
            text = sanitize_fn(text)
        text = text.strip()
        return text if text else None

    if isinstance(entry.get("content"), str):
        if not _should_include(message_phase):
            return None
        text = entry["content"]
        if sanitize_fn:
            text = sanitize_fn(text)
        text = text.strip()
        return text if text else None

    content = entry.get("content")
    if not isinstance(content, list):
        return None

    has_explicit_phased = any(
        isinstance(block, dict)
        and _is_assistant_text_content_block_type(block.get("type"))
        and parse_assistant_text_signature(block.get("textSignature"))
        and parse_assistant_text_signature(block.get("textSignature")).get("phase")
        for block in content
        if isinstance(block, dict)
    )

    if not phase and has_explicit_phased:
        return None

    parts: list[str] = []
    for block in content:
        if not isinstance(block, dict):
            continue
        record = block
        if not _is_assistant_text_content_block_type(record.get("type")) or not isinstance(record.get("text"), str):
            continue
        sig = parse_assistant_text_signature(record.get("textSignature"))
        resolved = sig.get("phase") if sig else None
        if resolved is None and not has_explicit_phased:
            resolved = message_phase
        if not _should_include(resolved):
            continue
        text = record["text"]
        if sanitize_fn:
            text = sanitize_fn(text)
        text = text.strip()
        if text:
            parts.append(text)

    if len(parts) == 0:
        return None
    return join_sep.join(parts)


def extract_assistant_visible_text(message: Any) -> str | None:
    final_answer = extract_assistant_text_for_phase(message, phase="final_answer")
    if final_answer:
        return final_answer
    return extract_assistant_text_for_phase(message)
