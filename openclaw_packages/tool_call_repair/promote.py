from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Optional, Set

from .payload import PlainTextToolCallBlock, parse_standalone_plain_text_tool_call_blocks


@dataclass
class PlainTextToolCallPromotionOptions:
    allowed_tool_names: Set[str] = field(default_factory=set)
    create_tool_call_block: Optional[Callable[[PlainTextToolCallBlock, str], dict]] = None
    allowed_stop_reasons: Optional[Set[Any]] = None
    message: Any = None
    require_assistant_role: bool = False
    resolve_tool_name: Optional[Callable[[str, Set[str]], Optional[str]]] = None
    is_retainable_non_text_block: Optional[Callable[[dict], bool]] = None


ToolCallRepairNameResolver = Callable[[str, Set[str]], Optional[str]]
PromotedPlainTextToolCallBlockFactory = Callable[[PlainTextToolCallBlock, str], dict]


def _as_record(value: Any) -> Optional[dict]:
    return value if isinstance(value, dict) else None


def _resolve_exact_tool_name(raw: str, allowed: Set[str]) -> Optional[str]:
    return raw if raw in allowed else None


def _create_promoted_blocks(text: str, opts: PlainTextToolCallPromotionOptions) -> Optional[list]:
    parsed = parse_standalone_plain_text_tool_call_blocks(text)
    if not parsed:
        return None
    resolver = opts.resolve_tool_name or _resolve_exact_tool_name
    tool_calls = []
    for block in parsed:
        resolved = resolver(block.name, opts.allowed_tool_names)
        if not resolved:
            return None
        factory = opts.create_tool_call_block or (lambda b, n: {"type": "tool_use", "name": n, "arguments": b.arguments})
        tool_calls.append(factory(block, resolved))
    return tool_calls


def _should_promote_message(opts: PlainTextToolCallPromotionOptions) -> bool:
    if len(opts.allowed_tool_names) == 0:
        return False
    record = _as_record(opts.message)
    if not record:
        return False
    if opts.require_assistant_role and record.get("role") != "assistant":
        return False
    if opts.allowed_stop_reasons:
        sr = record.get("stopReason")
        if sr not in opts.allowed_stop_reasons:
            return False
    return True


def extract_standalone_plain_text_tool_call_text(params: dict) -> Optional[str]:
    record = _as_record(params.get("message"))
    if not record:
        return None
    if params.get("requireAssistantRole") and record.get("role") != "assistant":
        return None
    allowed_sr = params.get("allowedStopReasons")
    if allowed_sr and record.get("stopReason") not in allowed_sr:
        return None
    content = record.get("content")
    if isinstance(content, str):
        text = content.strip()
        return text or None
    if not isinstance(content, list):
        return None
    text_parts = []
    for block in content:
        br = _as_record(block)
        if not br:
            return None
        if br.get("type") == "text":
            if not isinstance(br.get("text"), str):
                return None
            if br.get("text", "").strip():
                text_parts.append(br["text"])
            continue
        is_retainable = params.get("isRetainableNonTextBlock")
        allow_other = params.get("allowOtherNonTextBlocks")
        if is_retainable and callable(is_retainable) and is_retainable(br):
            continue
        if allow_other:
            continue
        return None
    text = "".join(text_parts).strip()
    return text or None


def promote_standalone_plain_text_tool_call_message(
    opts: PlainTextToolCallPromotionOptions,
) -> Optional[dict]:
    if not _should_promote_message(opts):
        return None
    record = _as_record(opts.message)
    if not record:
        return None
    original = record.get("content")
    if isinstance(original, str):
        text = original.strip()
        if not text:
            return None
        calls = _create_promoted_blocks(text, opts)
        if not calls:
            return None
        result = dict(record)
        result["content"] = calls
        result["stopReason"] = "toolUse"
        return result
    if not isinstance(original, list):
        return None
    content = []
    promoted_text_block = False
    text_parts: list[str] = []
    
    def _flush_text_parts() -> Optional[bool]:
        nonlocal text_parts
        if len(text_parts) == 0:
            return False
        calls = _create_promoted_blocks("".join(text_parts), opts)
        text_parts = []
        if not calls:
            return False
        if len(calls) == 0:
            return False
        content.extend(calls)
        return True

    for block in original:
        br = _as_record(block)
        if not br:
            return None
        if br.get("type") == "text":
            if not isinstance(br.get("text"), str):
                return None
            if br.get("text", "").strip():
                text_parts.append(br["text"])
            continue
        flushed = _flush_text_parts()
        if flushed is None:
            return None
        promoted_text_block = promoted_text_block or flushed
        is_retainable = opts.is_retainable_non_text_block
        if is_retainable and callable(is_retainable) and is_retainable(br):
            content.append(br)
            continue
        return None

    flushed_final = _flush_text_parts()
    if flushed_final is None:
        return None
    promoted_text_block = promoted_text_block or flushed_final
    if not promoted_text_block:
        return None
    result = dict(record)
    result["content"] = content
    result["stopReason"] = "toolUse"
    return result
