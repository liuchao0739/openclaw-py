from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Generic, List, Optional, TypeVar

from .chunk_text import chunk_text
from .ir import (
    MarkdownIR,
    MarkdownParseOptions,
    chunk_markdown_ir,
    markdown_to_ir,
    markdown_to_ir_with_meta,
    slice_markdown_ir,
)
from .render import RenderOptions, render_markdown_with_markers


T = TypeVar("T")


@dataclass
class RenderedMarkdownChunk:
    text: str = ""
    ir: Optional[MarkdownIR] = None
    start: int = 0
    end: int = 0


@dataclass
class RenderMarkdownIRChunksWithinLimitOptions:
    max_chars: int = 4000
    render_options: Optional[RenderOptions] = None
    parse_options: Optional[MarkdownParseOptions] = None
    chunk_overlap: int = 0
    include_metadata: bool = False


def _binary_search_max_chunk_size(
    ir: MarkdownIR,
    max_chars: int,
    render_fn: Callable[[MarkdownIR], str],
    min_size: int = 1,
    max_size: Optional[int] = None,
) -> int:
    if max_size is None:
        max_size = len(ir.text)

    if max_size <= 0:
        return 0

    rendered = render_fn(ir)
    if len(rendered) <= max_chars:
        return max_size

    lo = min_size
    hi = max_size
    result = 0

    while lo <= hi:
        mid = (lo + hi) // 2
        if mid <= 0:
            lo = mid + 1
            continue
        slice_ir = slice_markdown_ir(ir, 0, mid)
        rendered_len = len(render_fn(slice_ir))
        if rendered_len <= max_chars:
            result = mid
            lo = mid + 1
        else:
            hi = mid - 1

    return result


def _find_safe_break_point(
    ir: MarkdownIR,
    start: int,
    end: int,
    render_fn: Callable[[MarkdownIR], str],
    max_chars: int,
) -> int:
    search_start = start
    search_end = end

    while search_start < search_end:
        mid = (search_start + search_end) // 2
        if mid <= start:
            break
        slice_ir = slice_markdown_ir(ir, start, mid)
        rendered_len = len(render_fn(slice_ir))
        if rendered_len <= max_chars:
            search_start = mid
        else:
            search_end = mid - 1

    return max(search_start, start)


def render_markdown_ir_chunks_within_limit(
    ir: MarkdownIR,
    max_chars: int,
    render_options: Optional[RenderOptions] = None,
) -> List[RenderedMarkdownChunk]:
    if not ir.text:
        return []

    render_fn = lambda x: render_markdown_with_markers(x, render_options)

    rendered = render_fn(ir)
    if len(rendered) <= max_chars:
        return [
            RenderedMarkdownChunk(
                text=rendered,
                ir=ir,
                start=0,
                end=len(ir.text),
            )
        ]

    chunks: List[RenderedMarkdownChunk] = []
    cursor = 0
    total_len = len(ir.text)

    while cursor < total_len:
        remaining = total_len - cursor
        if remaining <= 0:
            break

        remaining_ir = slice_markdown_ir(ir, cursor, total_len)
        rendered_remaining = render_fn(remaining_ir)

        if len(rendered_remaining) <= max_chars:
            chunks.append(
                RenderedMarkdownChunk(
                    text=rendered_remaining,
                    ir=remaining_ir,
                    start=cursor,
                    end=total_len,
                )
            )
            break

        max_size = _binary_search_max_chunk_size(
            ir, max_chars, render_fn, min_size=1, max_size=remaining
        )

        if max_size <= 0:
            max_size = min(100, remaining)

        safe_end = _find_safe_break_point(
            ir, cursor, cursor + max_size, render_fn, max_chars
        )

        if safe_end <= cursor:
            safe_end = min(cursor + 1, total_len)

        slice_ir = slice_markdown_ir(ir, cursor, safe_end)
        rendered_slice = render_fn(slice_ir)

        chunks.append(
            RenderedMarkdownChunk(
                text=rendered_slice,
                ir=slice_ir,
                start=cursor,
                end=safe_end,
            )
        )

        cursor = safe_end
        while cursor < total_len and ir.text[cursor] in (" ", "\n", "\r", "\t"):
            cursor += 1

    return chunks


def chunk_ir_with_limit(
    ir: MarkdownIR,
    max_chars: int,
    render_options: Optional[RenderOptions] = None,
) -> List[MarkdownIR]:
    chunks = render_markdown_ir_chunks_within_limit(ir, max_chars, render_options)
    return [c.ir for c in chunks if c.ir is not None]


def render_markdown_chunks_within_limit(
    markdown: str,
    max_chars: int,
    render_options: Optional[RenderOptions] = None,
    parse_options: Optional[MarkdownParseOptions] = None,
) -> List[RenderedMarkdownChunk]:
    if parse_options is None:
        parse_options = MarkdownParseOptions()

    ir = markdown_to_ir(markdown, parse_options)
    return render_markdown_ir_chunks_within_limit(
        ir, max_chars, render_options
    )


def _estimate_rendered_size(ir: MarkdownIR) -> int:
    base_size = len(ir.text)
    extra = 0
    for style in ir.styles:
        if style.style == "bold":
            extra += 4
        elif style.style == "italic":
            extra += 2
        elif style.style == "code":
            extra += 2
        elif style.style == "strikethrough":
            extra += 4
    return base_size + extra


def _find_optimal_chunk_boundary(
    ir: MarkdownIR,
    start: int,
    limit: int,
    render_options: Optional[RenderOptions] = None,
) -> int:
    render_fn = lambda x: render_markdown_with_markers(x, render_options)
    remaining = len(ir.text) - start
    if remaining <= 0:
        return start

    max_size = min(remaining, limit)

    lo = 1
    hi = max_size
    best = 0

    while lo <= hi:
        mid = (lo + hi) // 2
        test_end = start + mid
        slice_ir = slice_markdown_ir(ir, start, test_end)
        rendered_len = len(render_fn(slice_ir))
        if rendered_len <= limit:
            best = mid
            lo = mid + 1
        else:
            hi = mid - 1

    return start + best if best > 0 else start + 1


def render_markdown_with_overlap(
    markdown: str,
    max_chars: int,
    overlap_chars: int = 0,
    render_options: Optional[RenderOptions] = None,
    parse_options: Optional[MarkdownParseOptions] = None,
) -> List[RenderedMarkdownChunk]:
    if parse_options is None:
        parse_options = MarkdownParseOptions()

    ir = markdown_to_ir(markdown, parse_options)

    render_fn = lambda x: render_markdown_with_markers(x, render_options)
    rendered_full = render_fn(ir)

    if len(rendered_full) <= max_chars:
        return [
            RenderedMarkdownChunk(
                text=rendered_full,
                ir=ir,
                start=0,
                end=len(ir.text),
            )
        ]

    chunks: List[RenderedMarkdownChunk] = []
    cursor = 0
    total_len = len(ir.text)

    while cursor < total_len:
        remaining = total_len - cursor

        if remaining <= 0:
            break

        rendered_remaining = render_fn(slice_markdown_ir(ir, cursor, total_len))
        if len(rendered_remaining) <= max_chars:
            chunks.append(
                RenderedMarkdownChunk(
                    text=rendered_remaining,
                    ir=slice_markdown_ir(ir, cursor, total_len),
                    start=cursor,
                    end=total_len,
                )
            )
            break

        boundary = _find_optimal_chunk_boundary(
            ir, cursor, max_chars, render_options
        )

        if boundary <= cursor:
            boundary = min(cursor + 1, total_len)

        end_pos = boundary
        if overlap_chars > 0 and end_pos < total_len:
            end_pos = min(end_pos + overlap_chars, total_len)

        chunk_ir = slice_markdown_ir(ir, cursor, end_pos)
        rendered = render_fn(chunk_ir)

        chunks.append(
            RenderedMarkdownChunk(
                text=rendered,
                ir=chunk_ir,
                start=cursor,
                end=end_pos,
            )
        )

        cursor = boundary
        while cursor < total_len and ir.text[cursor] in (" ", "\n", "\r", "\t"):
            cursor += 1

    return chunks