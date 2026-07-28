from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional

from .fences import FenceScanState, FenceSpan, scan_fence_spans


@dataclass
class InlineCodeState:
    open: bool = False
    ticks: int = 0


def create_inline_code_state() -> InlineCodeState:
    return InlineCodeState(open=False, ticks=0)


def parse_inline_code_spans(
    text: str,
    start_pos: int,
    end_pos: int,
    fence_spans: List[FenceSpan],
    inline_state: InlineCodeState,
) -> tuple:
    spans: List[tuple] = []
    pos = start_pos
    i = pos
    length = min(len(text), end_pos)

    while i < length:
        ch = text[i]

        if ch == "`":
            if inline_state.open:
                if ch == "`":
                    count = 0
                    scan = i
                    while scan < length and text[scan] == "`":
                        count += 1
                        scan += 1

                    if count == inline_state.ticks:
                        spans.append(
                            (pos, scan, inline_state.ticks)
                        )
                        inline_state.open = False
                        inline_state.ticks = 0
                        pos = scan
                        i = scan
                        continue
                    elif count < inline_state.ticks:
                        inline_state.ticks -= count
                        i = scan
                        continue
                    else:
                        inline_state.open = False
                        inline_state.ticks = 0
                        pos = scan
                        i = scan
                        continue
            else:
                pos = i
                count = 0
                scan = i
                while scan < length and text[scan] == "`":
                    count += 1
                    scan += 1
                inline_state.open = True
                inline_state.ticks = count
                i = scan
                continue
        else:
            if inline_state.open:
                if ch == "\n":
                    inline_state.open = False
                    inline_state.ticks = 0
                    pos = i
            i += 1

    if inline_state.open:
        inline_state.open = False
        inline_state.ticks = 0

    return spans, inline_state


def build_code_span_index(
    text: str,
    inline_state: Optional[InlineCodeState] = None,
    fence_state: Optional[FenceScanState] = None,
) -> dict:
    if inline_state is None:
        inline_state = create_inline_code_state()

    fence_result = scan_fence_spans(text, fence_state)
    fence_spans = fence_result["spans"]

    code_spans: List[tuple] = []
    pos = 0
    i = pos
    length = len(text)

    while i < length:
        fence_idx = 0
        in_fence = False
        for fs in fence_spans:
            line_no = text.count("\n", 0, i)
            if fs.start <= line_no <= fs.end:
                in_fence = True
                break
            fence_idx += 1

        if in_fence:
            i += 1
            pos = i
            continue

        ch = text[i]

        if ch == "`":
            count = 0
            scan = i
            while scan < length and text[scan] == "`":
                count += 1
                scan += 1

            if inline_state.open:
                if count == inline_state.ticks:
                    code_spans.append((pos, scan, inline_state.ticks))
                    inline_state.open = False
                    inline_state.ticks = 0
                    pos = scan
                    i = scan
                    continue
                elif count < inline_state.ticks:
                    inline_state.ticks -= count
                    i = scan
                    continue
                else:
                    inline_state.open = False
                    inline_state.ticks = 0
                    pos = scan
                    i = scan
                    continue
            else:
                pos = i
                inline_state.open = True
                inline_state.ticks = count
                i = scan
                continue
        else:
            if inline_state.open and ch == "\n":
                inline_state.open = False
                inline_state.ticks = 0
                pos = i
            i += 1

    if inline_state.open:
        inline_state.open = False
        inline_state.ticks = 0

    def is_inside(index: int) -> bool:
        for start, end, _ticks in code_spans:
            if start <= index <= end:
                return True
        return False

    return {
        "isInside": is_inside,
        "codeSpans": code_spans,
        "inlineState": inline_state,
    }