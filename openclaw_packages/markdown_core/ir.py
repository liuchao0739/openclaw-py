from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple, Union

try:
    from markdown_it import MarkdownIt
except ImportError:
    MarkdownIt = None

from .chunk_text import chunk_text
from .code_spans import build_code_span_index
from .fences import parse_fence_spans


MarkdownStyle = Literal[
    "bold",
    "italic",
    "underline",
    "strikethrough",
    "code",
    "link",
    "image",
    "inline_html",
    "inline_math",
    "display_math",
    "footnote",
    "highlight",
    "subscript",
    "superscript",
    "ruby",
]


@dataclass
class MarkdownStyleSpan:
    style: MarkdownStyle
    start: int
    end: int
    meta: Optional[Dict[str, Any]] = None


@dataclass
class MarkdownLinkSpan:
    target: str
    title: Optional[str] = None
    start: int = 0
    end: int = 0
    text_start: int = 0
    text_end: int = 0


@dataclass
class MarkdownIR:
    text: str = ""
    styles: List[MarkdownStyleSpan] = field(default_factory=list)
    links: List[MarkdownLinkSpan] = field(default_factory=list)
    blocks: List[Dict[str, Any]] = field(default_factory=list)


MarkdownTableAlignment = Literal["left", "center", "right", "none"]


@dataclass
class MarkdownTableCell:
    text: str = ""
    alignment: MarkdownTableAlignment = "none"
    is_header: bool = False
    colspan: int = 1


@dataclass
class MarkdownTableData:
    rows: List[List[MarkdownTableCell]] = field(default_factory=list)
    caption: Optional[str] = None


@dataclass
class MarkdownTableMeta:
    is_table: bool = False
    table: Optional[MarkdownTableData] = None
    start_line: int = 0
    end_line: int = 0


@dataclass
class MarkdownParseOptions:
    enable_tables: bool = True
    enable_frontmatter: bool = True
    enable_html: bool = False


@dataclass
class _RenderTarget:
    text: str = ""
    styles: List[MarkdownStyleSpan] = field(default_factory=list)
    links: List[MarkdownLinkSpan] = field(default_factory=list)


def _init_render_target() -> _RenderTarget:
    return _RenderTarget(text="", styles=[], links=[])


def _append_text(target: _RenderTarget, text: str) -> None:
    target.text += text


def _open_style(
    target: _RenderTarget, style: MarkdownStyle, start: int, meta: Optional[Dict[str, Any]] = None
) -> None:
    target.styles.append(
        MarkdownStyleSpan(style=style, start=start, end=start, meta=meta)
    )


def _close_style(target: _RenderTarget, style: MarkdownStyle, end: int) -> None:
    for i in range(len(target.styles) - 1, -1, -1):
        if target.styles[i].style == style and target.styles[i].end == target.styles[i].start:
            target.styles[i].end = end
            return
    target.styles.append(MarkdownStyleSpan(style=style, start=end, end=end))


def _add_link(
    target: _RenderTarget,
    target_url: str,
    text: str,
    title: Optional[str] = None,
    start: int = 0,
    end: int = 0,
    text_start: int = 0,
    text_end: int = 0,
) -> None:
    target.links.append(
        MarkdownLinkSpan(
            target=target_url,
            title=title,
            start=start,
            end=end,
            text_start=text_start,
            text_end=text_end,
        )
    )


def _process_inline_tokens(
    tokens: List[Any], target: _RenderTarget, meta: Optional[Dict[str, Any]] = None
) -> None:
    pos = len(target.text)
    for token in tokens:
        if token.type == "text":
            _append_text(target, token.content)
        elif token.type == "html_inline":
            _append_text(target, token.content)
        elif token.type == "inline":
            if hasattr(token, "children") and token.children:
                _process_inline_tokens(token.children, target, meta)
        elif token.type == "strong_open":
            _open_style(target, "bold", len(target.text), meta)
        elif token.type == "strong_close":
            _close_style(target, "bold", len(target.text))
        elif token.type == "em_open":
            _open_style(target, "italic", len(target.text), meta)
        elif token.type == "em_close":
            _close_style(target, "italic", len(target.text))
        elif token.type == "s_open":
            _open_style(target, "strikethrough", len(target.text), meta)
        elif token.type == "s_close":
            _close_style(target, "strikethrough", len(target.text))
        elif token.type == "code_inline":
            _open_style(target, "code", len(target.text), meta)
            _append_text(target, token.content)
            _close_style(target, "code", len(target.text))
        elif token.type == "link_open":
            href = ""
            title = None
            if hasattr(token, "attrs") and token.attrs:
                for attr in token.attrs:
                    if attr[0] == "href":
                        href = attr[1]
                    elif attr[0] == "title":
                        title = attr[1]
            _open_style(target, "link", len(target.text), meta)
            link_start = len(target.text)
        elif token.type == "link_close":
            _close_style(target, "link", len(target.text))
        elif token.type == "image":
            src = ""
            title = None
            if hasattr(token, "attrs") and token.attrs:
                for attr in token.attrs:
                    if attr[0] == "src":
                        src = attr[1]
                    elif attr[0] == "title":
                        title = attr[1]
            _open_style(target, "image", len(target.text), meta)
            _append_text(target, token.content or src)
            _close_style(target, "image", len(target.text))
        elif token.type == "softbreak":
            _append_text(target, "\n")
        elif token.type == "hardbreak":
            _append_text(target, "\n")
        elif token.type == "blockquote_open":
            pass
        elif token.type == "blockquote_close":
            pass
        elif token.type == "heading_open":
            level = 1
            if hasattr(token, "tag") and token.tag:
                try:
                    level = int(token.tag.replace("h", ""))
                except (ValueError, AttributeError):
                    level = 1
        elif token.type == "heading_close":
            pass
        elif token.type == "paragraph_open":
            pass
        elif token.type == "paragraph_close":
            pass


def _parse_blocks(md: str, options: MarkdownParseOptions) -> Tuple[_RenderTarget, List[Dict[str, Any]]]:
    if MarkdownIt is None:
        raise ImportError("markdown-it-py is required. Install with: pip install markdown-it-py")

    target = _init_render_target()
    blocks: List[Dict[str, Any]] = []

    md_parser = MarkdownIt("commonmark", {"html": options.enable_html})
    md_parser.enable("table", options.enable_tables)
    md_parser.enable("strikethrough", True)

    tokens = md_parser.parse(md)

    current_block_start = 0
    in_paragraph = False
    in_heading = False
    in_blockquote = False
    in_list = False
    in_code_block = False
    current_code_content = ""
    current_code_lang = ""

    i = 0
    while i < len(tokens):
        token = tokens[i]

        if token.type == "heading_open":
            level = 1
            if hasattr(token, "tag") and token.tag:
                try:
                    level = int(token.tag.replace("h", ""))
                except (ValueError, AttributeError):
                    level = 1
            blocks.append({"type": "heading", "level": level, "start": len(target.text)})
            in_heading = True
        elif token.type == "heading_close":
            if in_heading:
                blocks[-1]["end"] = len(target.text)
                blocks.append({"type": "paragraph_end", "start": len(target.text)})
                in_heading = False
        elif token.type == "paragraph_open":
            blocks.append({"type": "paragraph", "start": len(target.text)})
            in_paragraph = True
        elif token.type == "paragraph_close":
            if in_paragraph:
                blocks[-1]["end"] = len(target.text)
                blocks.append({"type": "paragraph_end", "start": len(target.text)})
                in_paragraph = False
        elif token.type == "inline":
            if in_code_block:
                pass
            else:
                _process_inline_tokens([token], target)
        elif token.type == "code_block":
            blocks.append({"type": "code_block", "start": len(target.text)})
            if hasattr(token, "content"):
                _append_text(target, token.content)
            blocks[-1]["end"] = len(target.text)
            blocks.append({"type": "paragraph_end", "start": len(target.text)})
        elif token.type == "blockquote_open":
            blocks.append({"type": "blockquote", "start": len(target.text)})
            in_blockquote = True
        elif token.type == "blockquote_close":
            if in_blockquote:
                blocks[-1]["end"] = len(target.text)
                blocks.append({"type": "paragraph_end", "start": len(target.text)})
                in_blockquote = False
        elif token.type == "bullet_list_open":
            blocks.append({"type": "list", "list_type": "bullet", "start": len(target.text)})
            in_list = True
        elif token.type == "ordered_list_open":
            blocks.append({"type": "list", "list_type": "ordered", "start": len(target.text)})
            in_list = True
        elif token.type == "bullet_list_close" or token.type == "ordered_list_close":
            if in_list and blocks:
                blocks[-1]["end"] = len(target.text)
                blocks.append({"type": "paragraph_end", "start": len(target.text)})
                in_list = False
        elif token.type == "list_item_open":
            pass
        elif token.type == "list_item_close":
            pass
        elif token.type == "table_open":
            blocks.append({"type": "table", "start": len(target.text)})
        elif token.type == "table_close":
            if blocks and blocks[-1]["type"] == "table":
                blocks[-1]["end"] = len(target.text)
                blocks.append({"type": "paragraph_end", "start": len(target.text)})
        elif token.type == "tr_open":
            pass
        elif token.type == "tr_close":
            pass
        elif token.type == "td_open" or token.type == "th_open":
            pass
        elif token.type == "td_close" or token.type == "th_close":
            pass
        elif token.type == "hr":
            blocks.append({"type": "hr", "start": len(target.text), "end": len(target.text)})
        elif token.type == "footnote_ref":
            pass
        elif token.type == "footnote_block_open":
            blocks.append({"type": "footnote", "start": len(target.text)})
        elif token.type == "footnote_block_close":
            if blocks and blocks[-1]["type"] == "footnote":
                blocks[-1]["end"] = len(target.text)
                blocks.append({"type": "paragraph_end", "start": len(target.text)})
        elif token.type == "html_block":
            if hasattr(token, "content"):
                blocks.append({"type": "html_block", "start": len(target.text)})
                _append_text(target, token.content)
                blocks[-1]["end"] = len(target.text)
                blocks.append({"type": "paragraph_end", "start": len(target.text)})

        i += 1

    return target, blocks


def _trim_cell(text: str) -> str:
    return text.strip()


def _append_cell(
    row: List[MarkdownTableCell],
    text: str,
    alignment: MarkdownTableAlignment = "none",
    is_header: bool = False,
) -> None:
    row.append(
        MarkdownTableCell(text=text, alignment=alignment, is_header=is_header)
    )


def _parse_table_cells(line: str) -> List[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    cells = [c.strip() for c in line.split("|")]
    return cells


def _parse_table_alignment(line: str) -> List[MarkdownTableAlignment]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    cells = [c.strip() for c in line.split("|")]
    alignments: List[MarkdownTableAlignment] = []
    for cell in cells:
        cell = cell.strip()
        if cell.startswith(":") and cell.endswith(":"):
            alignments.append("center")
        elif cell.endswith(":"):
            alignments.append("right")
        elif cell.startswith(":"):
            alignments.append("left")
        else:
            alignments.append("none")
    return alignments


def _is_table_separator_row(line: str) -> bool:
    line = line.strip()
    if not line.startswith("|") and not line.startswith("+"):
        return False
    stripped = line
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    if stripped.startswith("+"):
        stripped = stripped[1:]
    if stripped.endswith("+"):
        stripped = stripped[:-1]
    cells = [c.strip() for c in stripped.split("|")]
    if len(cells) < 2:
        return False
    for cell in cells:
        cell = cell.strip()
        if not re.match(r'^:?-{3,}:?$', cell):
            return False
    return True


def _collect_table_block(
    lines: List[str], start_line: int
) -> Tuple[Optional[MarkdownTableData], int, int]:
    if start_line >= len(lines):
        return None, start_line, start_line

    first_line = lines[start_line].strip()
    if "|" not in first_line:
        return None, start_line, start_line

    end_line = start_line
    while end_line < len(lines):
        line = lines[end_line].strip()
        if not line:
            break
        if "|" not in line:
            break
        end_line += 1

    if end_line - start_line < 2:
        return None, start_line, start_line

    has_separator = False
    separator_idx = -1
    for idx in range(start_line, end_line):
        if _is_table_separator_row(lines[idx]):
            has_separator = True
            separator_idx = idx
            break

    if not has_separator:
        return None, start_line, start_line

    header_line = lines[start_line]
    header_cells = _parse_table_cells(header_line)
    alignments = _parse_table_alignment(lines[separator_idx])

    data = MarkdownTableData()

    header_row: List[MarkdownTableCell] = []
    for ci, cell_text in enumerate(header_cells):
        alignment = alignments[ci] if ci < len(alignments) else "none"
        is_header = True
        _append_cell(header_row, _trim_cell(cell_text), alignment, is_header)
    data.rows.append(header_row)

    for idx in range(separator_idx + 1, end_line):
        line = lines[idx]
        if not line.strip():
            continue
        cells = _parse_table_cells(line)
        row: List[MarkdownTableCell] = []
        for ci, cell_text in enumerate(cells):
            alignment = alignments[ci] if ci < len(alignments) else "none"
            _append_cell(row, _trim_cell(cell_text), alignment, False)
        if row:
            data.rows.append(row)

    return data, start_line, end_line


def _render_table_as_bullets(table: MarkdownTableData) -> str:
    lines: List[str] = []
    if table.caption:
        lines.append(table.caption)
    for row in table.rows:
        for cell in row:
            prefix = "**" if cell.is_header else "- "
            suffix = "**" if cell.is_header else ""
            lines.append(f"{prefix}{cell.text}{suffix}")
    return "\n".join(lines)


def _render_table_as_code(table: MarkdownTableData) -> str:
    lines: List[str] = []
    lines.append("```")
    for row in table.rows:
        cells = [cell.text for cell in row]
        lines.append(" | ".join(cells))
    lines.append("```")
    return "\n".join(lines)


def _find_tables_in_text(text: str) -> List[MarkdownTableMeta]:
    lines = text.split("\n")
    tables: List[MarkdownTableMeta] = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if "|" in line and not line.startswith("#"):
            table_data, start, end = _collect_table_block(lines, i)
            if table_data is not None:
                tables.append(
                    MarkdownTableMeta(
                        is_table=True,
                        table=table_data,
                        start_line=start,
                        end_line=end,
                    )
                )
                i = end
                continue
        i += 1
    return tables


def markdown_to_ir(md: str, options: Optional[MarkdownParseOptions] = None) -> MarkdownIR:
    if options is None:
        options = MarkdownParseOptions()

    target, blocks = _parse_blocks(md, options)

    return MarkdownIR(
        text=target.text,
        styles=target.styles,
        links=target.links,
        blocks=blocks,
    )


def markdown_to_ir_with_meta(
    md: str, options: Optional[MarkdownParseOptions] = None
) -> Tuple[MarkdownIR, Dict[str, Any]]:
    if options is None:
        options = MarkdownParseOptions()

    ir = markdown_to_ir(md, options)

    tables = _find_tables_in_text(md)
    meta: Dict[str, Any] = {"tables": tables}

    return ir, meta


def chunk_markdown_ir(
    ir: MarkdownIR, limit: int, options: Optional[MarkdownParseOptions] = None
) -> List[MarkdownIR]:
    text_chunks = chunk_text(ir.text, limit)

    if len(text_chunks) == 1:
        return [ir]

    result: List[MarkdownIR] = []
    offset = 0

    for chunk in text_chunks:
        chunk_start = offset
        chunk_end = offset + len(chunk)

        chunk_styles: List[MarkdownStyleSpan] = []
        for style in ir.styles:
            s = max(style.start, chunk_start)
            e = min(style.end, chunk_end)
            if s < e:
                chunk_styles.append(
                    MarkdownStyleSpan(
                        style=style.style,
                        start=s - chunk_start,
                        end=e - chunk_start,
                        meta=style.meta,
                    )
                )

        chunk_links: List[MarkdownLinkSpan] = []
        for link in ir.links:
            ls = max(link.start, chunk_start)
            le = min(link.end, chunk_end)
            if ls < le:
                chunk_links.append(
                    MarkdownLinkSpan(
                        target=link.target,
                        title=link.title,
                        start=ls - chunk_start,
                        end=le - chunk_start,
                        text_start=max(link.text_start, chunk_start) - chunk_start,
                        text_end=min(link.text_end, chunk_end) - chunk_start,
                    )
                )

        result.append(
            MarkdownIR(
                text=chunk,
                styles=chunk_styles,
                links=chunk_links,
                blocks=[],
            )
        )

        offset = chunk_end
        while offset < len(ir.text) and ir.text[offset] in (" ", "\n", "\r", "\t"):
            offset += 1

    return result


def slice_markdown_ir(
    ir: MarkdownIR, start: int, end: int
) -> MarkdownIR:
    new_text = ir.text[start:end]

    new_styles: List[MarkdownStyleSpan] = []
    for style in ir.styles:
        s = max(style.start, start)
        e = min(style.end, end)
        if s < e:
            new_styles.append(
                MarkdownStyleSpan(
                    style=style.style,
                    start=s - start,
                    end=e - start,
                    meta=style.meta,
                )
            )

    new_links: List[MarkdownLinkSpan] = []
    for link in ir.links:
        ls = max(link.start, start)
        le = min(link.end, end)
        if ls < le:
            new_links.append(
                MarkdownLinkSpan(
                    target=link.target,
                    title=link.title,
                    start=ls - start,
                    end=le - start,
                    text_start=max(link.text_start, start) - start,
                    text_end=min(link.text_end, end) - start,
                )
            )

    return MarkdownIR(text=new_text, styles=new_styles, links=new_links, blocks=[])


def merge_style_spans(
    spans: List[MarkdownStyleSpan],
) -> List[MarkdownStyleSpan]:
    if not spans:
        return []

    sorted_spans = sorted(spans, key=lambda s: (s.start, s.end))
    merged: List[MarkdownStyleSpan] = []

    for span in sorted_spans:
        if merged and span.start <= merged[-1].end:
            merged[-1].end = max(merged[-1].end, span.end)
        else:
            merged.append(
                MarkdownStyleSpan(
                    style=span.style,
                    start=span.start,
                    end=span.end,
                    meta=span.meta,
                )
            )

    return merged


def clamp_style_spans(
    spans: List[MarkdownStyleSpan], start: int, end: int
) -> List[MarkdownStyleSpan]:
    result: List[MarkdownStyleSpan] = []
    for span in spans:
        s = max(span.start, start)
        e = min(span.end, end)
        if s < e:
            result.append(
                MarkdownStyleSpan(
                    style=span.style,
                    start=s,
                    end=e,
                    meta=span.meta,
                )
            )
    return result


def slice_style_spans(
    spans: List[MarkdownStyleSpan], start: int, end: int
) -> List[MarkdownStyleSpan]:
    result: List[MarkdownStyleSpan] = []
    for span in spans:
        s = max(span.start, start)
        e = min(span.end, end)
        if s < e:
            result.append(
                MarkdownStyleSpan(
                    style=span.style,
                    start=s - start,
                    end=e - start,
                    meta=span.meta,
                )
            )
    return result