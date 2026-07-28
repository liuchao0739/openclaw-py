from __future__ import annotations

from typing import List, Literal, Optional

from .ir import (
    MarkdownIR,
    MarkdownParseOptions,
    MarkdownTableData,
    MarkdownTableMeta,
    _find_tables_in_text,
    _render_table_as_bullets,
    _render_table_as_code,
    markdown_to_ir_with_meta,
)
from .render import RenderOptions, render_markdown_with_markers

MarkdownTableMode = Literal["off", "bullets", "code", "block"]


def convert_markdown_tables(
    markdown: str,
    mode: MarkdownTableMode = "bullets",
) -> str:
    if mode == "off":
        return markdown

    tables = _find_tables_in_text(markdown)
    if not tables:
        return markdown

    result_lines: List[str] = []
    lines = markdown.split("\n")
    processed_up_to = 0

    for table_meta in tables:
        if table_meta.table is None:
            continue

        start_line = table_meta.start_line
        end_line = table_meta.end_line

        if start_line > processed_up_to:
            result_lines.extend(lines[processed_up_to:start_line])

        if mode == "bullets":
            rendered = _render_table_as_bullets(table_meta.table)
        elif mode == "code":
            rendered = _render_table_as_code(table_meta.table)
        elif mode == "block":
            rendered = _render_table_as_code(table_meta.table)
        else:
            rendered = _render_table_as_bullets(table_meta.table)

        result_lines.append(rendered)
        processed_up_to = end_line

    if processed_up_to < len(lines):
        result_lines.extend(lines[processed_up_to:])

    return "\n".join(result_lines)


def convert_tables_in_ir(
    ir: MarkdownIR,
    mode: MarkdownTableMode = "bullets",
    options: Optional[MarkdownParseOptions] = None,
) -> MarkdownIR:
    if mode == "off":
        return ir

    if options is None:
        options = MarkdownParseOptions()

    rendered = render_markdown_with_markers(ir)
    converted = convert_markdown_tables(rendered, mode)

    new_ir, _meta = markdown_to_ir_with_meta(converted, options)
    return new_ir


def detect_tables(markdown: str) -> List[MarkdownTableMeta]:
    return _find_tables_in_text(markdown)


def table_to_text(table: MarkdownTableData, mode: MarkdownTableMode = "bullets") -> str:
    if mode == "code" or mode == "block":
        return _render_table_as_code(table)
    return _render_table_as_bullets(table)