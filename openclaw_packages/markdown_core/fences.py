from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class FenceSpan:
    start: int
    end: int
    open_line: int
    marker: str
    indent: int


@dataclass
class FenceScanState:
    at_line_start: bool = True
    open: Optional[Dict] = None

    def reset(self) -> None:
        self.at_line_start = True
        self.open = None


def scan_fence_spans(
    buffer: str, state: Optional[FenceScanState] = None
) -> dict:
    if state is None:
        state = FenceScanState()

    spans: List[FenceSpan] = []
    pos = 0
    length = len(buffer)

    while pos < length:
        ch = buffer[pos]

        if state.at_line_start:
            if state.open is not None:
                marker_char = state.open["marker_char"]
                marker_len = state.open["marker_len"]
                open_line = state.open["open_line"]
                indent = state.open["indent"]

                if ch == marker_char:
                    count = 0
                    scan = pos
                    while scan < length and buffer[scan] == marker_char:
                        count += 1
                        scan += 1

                    if count >= marker_len:
                        rest = scan
                        while rest < length and buffer[rest] in (" ", "\t"):
                            rest += 1
                        if rest >= length or buffer[rest] == "\n":
                            end_line = _count_lines(buffer, scan)
                            spans.append(
                                FenceSpan(
                                    start=open_line,
                                    end=end_line,
                                    open_line=open_line,
                                    marker=marker_char * marker_len,
                                    indent=indent,
                                )
                            )
                            state.open = None
                            pos = rest
                            if pos < length and buffer[pos] == "\n":
                                pos += 1
                                state.at_line_start = True
                            continue
                    pos = scan
                    continue
                else:
                    if ch == "\n":
                        pos += 1
                        state.at_line_start = True
                        continue
                    pos += 1
                    continue
            else:
                if ch in ("`", "~"):
                    marker_char = ch
                    count = 0
                    scan = pos
                    while scan < length and buffer[scan] == marker_char:
                        count += 1
                        scan += 1

                    if count >= 3:
                        indent = 0
                        temp = pos
                        while temp < length and buffer[temp] in (" ", "\t"):
                            indent += 1
                            temp += 1

                        state.open = {
                            "marker_char": marker_char,
                            "marker_len": count,
                            "open_line": _count_lines(buffer, pos),
                            "marker": marker_char * count,
                            "indent": indent,
                        }
                        pos = scan
                        while pos < length and buffer[pos] not in ("\n", "\r"):
                            pos += 1
                        continue
                    else:
                        if ch == "\n":
                            pos += 1
                            state.at_line_start = True
                            continue
                        pos += 1
                        continue
                else:
                    if ch == "\n":
                        pos += 1
                        state.at_line_start = True
                        continue
                    pos += 1
                    continue
        else:
            if ch == "\n":
                pos += 1
                state.at_line_start = True
                continue
            pos += 1

    return {"spans": spans, "state": state}


def _count_lines(buffer: str, pos: int) -> int:
    return buffer.count("\n", 0, pos)


def parse_fence_spans(buffer: str) -> List[FenceSpan]:
    result = scan_fence_spans(buffer)
    return result["spans"]


def find_fence_span_at(
    spans: List[FenceSpan], index: int
) -> Optional[FenceSpan]:
    lo = 0
    hi = len(spans) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        span = spans[mid]
        if span.start <= index <= span.end:
            return span
        elif index < span.start:
            hi = mid - 1
        else:
            lo = mid + 1
    return None


def is_safe_fence_break(
    spans: List[FenceSpan], index: int
) -> bool:
    span = find_fence_span_at(spans, index)
    if span is None:
        return True
    return False