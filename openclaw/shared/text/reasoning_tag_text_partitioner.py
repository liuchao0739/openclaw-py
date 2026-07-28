from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from openclaw_packages.markdown_core import (
    FenceScanState,
    InlineCodeState,
    build_code_span_index,
    create_inline_code_state,
)

ReasoningTagTextDeltaKind = Literal["text", "thinking"]


@dataclass(frozen=True)
class ReasoningTagTextDelta:
    kind: ReasoningTagTextDeltaKind
    text: str


_REASONING_TAG_RE = re.compile(
    r"<\s*(\/?)\s*(?:(?:antml:|mm:)?(?:think(?:ing)?|thought|reasoning)|antthinking)\b[^<>]*>",
    re.IGNORECASE,
)
_REASONING_TAG_NAMES = (
    "think",
    "thinking",
    "thought",
    "reasoning",
    "antthinking",
    "antml:think",
    "antml:thinking",
    "antml:thought",
    "antml:reasoning",
    "mm:think",
    "mm:thinking",
    "mm:thought",
    "mm:reasoning",
)


class ReasoningTagTextPartitioner:
    def mark_strict(self) -> None:  # pragma: no cover - stateful API
        ...

    def push(self, chunk: str) -> list[ReasoningTagTextDelta]:  # pragma: no cover
        ...

    def push_visible(self, chunk: str) -> list[ReasoningTagTextDelta]:  # pragma: no cover
        ...

    def flush(self) -> list[ReasoningTagTextDelta]:  # pragma: no cover
        ...

    def has_pending(self) -> bool:  # pragma: no cover
        ...

    def is_inside_reasoning(self) -> bool:  # pragma: no cover
        ...


def _has_raw_reasoning_tag(text: str) -> bool:
    return bool(_REASONING_TAG_RE.search(text))


def _has_raw_reasoning_close_tag(text: str) -> bool:
    for match in _REASONING_TAG_RE.finditer(text):
        if match.group(1) == "/":
            return True
    return False


def _find_next_reasoning_tag(
    text: str,
    is_index_inside_code,
) -> tuple[int, str, bool] | None:
    for match in _REASONING_TAG_RE.finditer(text):
        if not is_index_inside_code(match.start()):
            return (match.start(), match.group(0), match.group(1) == "/")
    return None


def _reasoning_tag_prefix_suffix_index(
    text: str,
    is_index_inside_code,
) -> int:
    idx = text.rfind("<")
    while idx >= 0:
        if not is_index_inside_code(idx) and _is_reasoning_tag_prefix(text[idx:]):
            return idx
        if idx == 0:
            break
        idx = text.rfind("<", 0, idx)
    return -1


def _is_reasoning_tag_prefix(text: str) -> bool:
    name = _normalize_reasoning_tag_prefix_name(text)
    for tag_name in _REASONING_TAG_NAMES:
        if name.startswith(tag_name):
            if len(name) == len(tag_name):
                return True
            rest = name[len(tag_name):]
            if not rest or re.match(r"^[\s/>]", rest):
                return True
    return False


def _is_reasoning_close_tag_prefix(text: str) -> bool:
    normalized = re.sub(r"^<\s*/", "<", text, count=1)
    normalized = re.sub(r"^<\s*\s*/", "</", normalized, count=1)
    if normalized.startswith("<") and not normalized.startswith("</"):
        normalized = re.sub(r"^<\/", "</", normalized, count=1)
    normalized = normalized.lower()
    return normalized.startswith("</") and _is_reasoning_tag_prefix(text)


def _normalize_reasoning_tag_prefix_name(text: str) -> str:
    normalized = re.sub(r"^<\s*/", "<", text, count=1)
    normalized = re.sub(r"^<\s*\s*/", "</", normalized, count=1)
    if normalized.startswith("<") and not normalized.startswith("</"):
        normalized = re.sub(r"^<\/", "</", normalized, count=1)
    if normalized.startswith("</"):
        raw_name = normalized[2:]
    else:
        raw_name = normalized[1:]
    return raw_name.lstrip()


def _find_open_code_context_start(text: str) -> int:
    fence = _find_open_fence_start(text)
    inline = _find_open_inline_code_start(text)
    if fence == -1:
        return inline
    if inline == -1:
        return fence
    return min(fence, inline)


def _find_open_inline_code_start(text: str) -> int:
    open_start = -1
    open_ticks = 0
    index = 0
    while index < len(text):
        if text[index] != "`":
            index += 1
            continue
        run_start = index
        run_length = 0
        while index < len(text) and text[index] == "`":
            run_length += 1
            index += 1
        if open_start == -1:
            open_start = run_start
            open_ticks = run_length
        elif run_length == open_ticks:
            open_start = -1
            open_ticks = 0
    return open_start


_FENCE_RE = re.compile(r"(?:^|\n)(```|~~~)[^\n]*(?:\n|$)")


def _find_open_fence_start(text: str) -> int:
    open_marker: str | None = None
    open_index = -1
    for match in _FENCE_RE.finditer(text):
        marker = match.group(1)
        if open_marker is not None and open_marker == marker:
            open_marker = None
            open_index = -1
        elif open_marker is None:
            open_marker = marker
            prefix_len = len(match.group(0)) - len(match.group(0).lstrip("\r\n"))
            open_index = match.start() + prefix_len
    return open_index


def _find_trailing_fence_fragment_start(
    text: str,
    inline_state: InlineCodeState,
    fence_state: FenceScanState | None,
) -> int:
    if inline_state.open or (fence_state is not None and fence_state.open is not None):
        return -1
    line_start = max(text.rfind("\n") + 1, 0)
    line = text[line_start:]
    if re.match(r"^( {0,3})(`{1,2}|~{1,2})$", line):
        return line_start
    return -1


def create_reasoning_tag_text_partitioner() -> ReasoningTagTextPartitioner:
    buffer = ""
    reasoning_depth = 0
    strict_mode = False
    emitted_visible_text = False
    inline_code_state = create_inline_code_state()
    fence_state: FenceScanState | None = None
    hidden_inline_code_state = create_inline_code_state()
    hidden_fence_state: FenceScanState | None = None
    recoverable_open_tag_text: str | None = None

    def emit(kind: ReasoningTagTextDeltaKind, text: str) -> None:
        nonlocal inline_code_state, fence_state, hidden_inline_code_state, hidden_fence_state, emitted_visible_text
        if not text:
            return
        if kind == "text" and text.strip():
            emitted_visible_text = True
        if kind == "text":
            next_code = build_code_span_index(text, inline_code_state, fence_state)
            inline_code_state = next_code["inlineState"]
            fence_state = next_code.get("state", fence_state) if "state" in next_code else fence_state
        else:
            next_code = build_code_span_index(
                text, hidden_inline_code_state, hidden_fence_state
            )
            hidden_inline_code_state = next_code["inlineState"]
            hidden_fence_state = next_code.get("state", hidden_fence_state) if "state" in next_code else hidden_fence_state
        output_list = output["list"]
        if output_list and output_list[-1].kind == kind:
            output_list[-1] = ReasoningTagTextDelta(
                kind=kind, text=output_list[-1].text + text
            )
        else:
            output_list.append(ReasoningTagTextDelta(kind=kind, text=text))

    output = {"list": []}

    def consume(final: bool, recover_full_unclosed: bool) -> list[ReasoningTagTextDelta]:
        nonlocal buffer, reasoning_depth, recoverable_open_tag_text, inline_code_state, fence_state
        nonlocal hidden_inline_code_state, hidden_fence_state, emitted_visible_text
        output["list"] = []

        while buffer:
            active_inline_code_state = (
                inline_code_state
                if reasoning_depth == 0
                else hidden_inline_code_state
            )
            active_fence_state = (
                fence_state if reasoning_depth == 0 else hidden_fence_state
            )
            code_spans = build_code_span_index(
                buffer, active_inline_code_state, active_fence_state
            )
            has_unclosed_code = (
                reasoning_depth == 0
                and bool(
                    getattr(code_spans["inlineState"], "open", False)
                    or (
                        code_spans.get("state") is not None
                        and getattr(code_spans["state"], "open", None) is not None
                    )
                )
            )
            has_raw_reasoning = _has_raw_reasoning_tag(buffer)
            code_spans_is_inside = code_spans.get("isInside", lambda _i: False)

            tag = _find_next_reasoning_tag(
                buffer,
                lambda index: (
                    False
                    if final and has_unclosed_code and has_raw_reasoning
                    else code_spans_is_inside(index)
                ),
            )
            if tag is None:
                if final:
                    recover_as_text = (
                        reasoning_depth > 0
                        and recover_full_unclosed
                        and not _has_raw_reasoning_close_tag(buffer)
                    )
                    recovered_text = (
                        (recoverable_open_tag_text or "") + buffer
                        if recover_as_text
                        else buffer
                    )
                    emit(
                        "thinking"
                        if reasoning_depth > 0 and not recover_as_text
                        else "text",
                        recovered_text,
                    )
                    buffer = ""
                    reasoning_depth = 0
                    recoverable_open_tag_text = None
                    return list(output["list"])
                if (
                    reasoning_depth > 0
                    and recover_full_unclosed
                    and (not emitted_visible_text or recoverable_open_tag_text)
                ):
                    return list(output["list"])
                if has_unclosed_code and has_raw_reasoning:
                    open_code_index = (
                        0
                        if getattr(inline_code_state, "open", False)
                        or (fence_state is not None and fence_state.open is not None)
                        else _find_open_code_context_start(buffer)
                    )
                    if open_code_index != -1:
                        emit("text", buffer[:open_code_index])
                        buffer = buffer[open_code_index:]
                        return list(output["list"])
                    return list(output["list"])
                trailing_fence_start = _find_trailing_fence_fragment_start(
                    buffer,
                    active_inline_code_state,
                    active_fence_state,
                )
                if trailing_fence_start != -1:
                    emit(
                        "thinking" if reasoning_depth > 0 else "text",
                        buffer[:trailing_fence_start],
                    )
                    buffer = buffer[trailing_fence_start:]
                    return list(output["list"])
                keep_from = _reasoning_tag_prefix_suffix_index(
                    buffer,
                    lambda index: code_spans_is_inside(index),
                )
                if keep_from == -1:
                    emit(
                        "thinking" if reasoning_depth > 0 else "text",
                        buffer,
                    )
                    buffer = ""
                    return list(output["list"])
                if (
                    reasoning_depth == 0
                    and keep_from > 0
                    and buffer[:keep_from].strip()
                    and _is_reasoning_close_tag_prefix(buffer[keep_from:])
                ):
                    return list(output["list"])
                if keep_from > 0:
                    emit(
                        "thinking" if reasoning_depth > 0 else "text",
                        buffer[:keep_from],
                    )
                    buffer = buffer[keep_from:]
                return list(output["list"])

            tag_index, tag_text, is_close = tag
            before_tag = buffer[:tag_index]
            after_tag = buffer[tag_index + len(tag_text):]
            if is_close and reasoning_depth == 0:
                if recover_full_unclosed and before_tag.strip() and after_tag.strip():
                    emit("text", before_tag + tag_text)
                    buffer = after_tag
                    continue
                if before_tag.strip() and not after_tag.strip() and not final:
                    return list(output["list"])
                if not before_tag.strip() or not after_tag.strip():
                    emit("text", before_tag)
                buffer = after_tag
                continue

            emit(
                "thinking" if reasoning_depth > 0 else "text",
                buffer[:tag_index],
            )
            buffer = after_tag
            if is_close:
                reasoning_depth = max(0, reasoning_depth - 1)
                if reasoning_depth == 0:
                    recoverable_open_tag_text = None
                    hidden_inline_code_state = create_inline_code_state()
                    hidden_fence_state = None
            else:
                if reasoning_depth == 0:
                    recoverable_open_tag_text = (
                        tag_text if recover_full_unclosed and emitted_visible_text else None
                    )
                    hidden_inline_code_state = create_inline_code_state()
                    hidden_fence_state = None
                reasoning_depth += 1

        return list(output["list"])

    class _Partitioner(ReasoningTagTextPartitioner):
        def mark_strict(self) -> None:
            nonlocal strict_mode
            strict_mode = True

        def push(self, chunk: str) -> list[ReasoningTagTextDelta]:
            nonlocal buffer, strict_mode
            strict_mode = True
            buffer += chunk
            return consume(False, False)

        def push_visible(self, chunk: str) -> list[ReasoningTagTextDelta]:
            nonlocal buffer
            buffer += chunk
            return consume(False, True)

        def flush(self) -> list[ReasoningTagTextDelta]:
            return consume(True, not strict_mode)

        def has_pending(self) -> bool:
            return bool(buffer) or reasoning_depth > 0

        def is_inside_reasoning(self) -> bool:
            return reasoning_depth > 0

    return _Partitioner()
