from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .ir import MarkdownIR, MarkdownStyle, MarkdownStyleSpan


@dataclass
class RenderStyleMarker:
    style: MarkdownStyle
    open: str
    close: str
    escape: Optional[str] = None


@dataclass
class RenderStyleMap:
    bold: Optional[RenderStyleMarker] = None
    italic: Optional[RenderStyleMarker] = None
    underline: Optional[RenderStyleMarker] = None
    strikethrough: Optional[RenderStyleMarker] = None
    code: Optional[RenderStyleMarker] = None
    link: Optional[RenderStyleMarker] = None
    image: Optional[RenderStyleMarker] = None
    inline_html: Optional[RenderStyleMarker] = None
    inline_math: Optional[RenderStyleMarker] = None
    display_math: Optional[RenderStyleMarker] = None
    footnote: Optional[RenderStyleMarker] = None
    highlight: Optional[RenderStyleMarker] = None
    subscript: Optional[RenderStyleMarker] = None
    superscript: Optional[RenderStyleMarker] = None
    ruby: Optional[RenderStyleMarker] = None


STYLE_ORDER: List[MarkdownStyle] = [
    "underline",
    "strikethrough",
    "highlight",
    "superscript",
    "subscript",
    "bold",
    "italic",
    "code",
    "link",
    "image",
    "inline_html",
    "inline_math",
    "display_math",
    "footnote",
    "ruby",
]

STYLE_RANK: Dict[MarkdownStyle, int] = {
    "underline": 1,
    "strikethrough": 2,
    "highlight": 3,
    "superscript": 4,
    "subscript": 5,
    "bold": 6,
    "italic": 7,
    "code": 8,
    "link": 9,
    "image": 10,
    "inline_html": 11,
    "inline_math": 12,
    "display_math": 13,
    "footnote": 14,
    "ruby": 15,
}


@dataclass
class RenderLink:
    target: str
    title: Optional[str] = None
    text: str = ""


@dataclass
class RenderOptions:
    style_map: Optional[RenderStyleMap] = None
    link_handler: Optional[Callable[[RenderLink], str]] = None
    escape_html: bool = False


def _get_style_marker(
    style: MarkdownStyle, style_map: Optional[RenderStyleMap]
) -> Optional[RenderStyleMarker]:
    if style_map is not None:
        return getattr(style_map, style, None)
    return None


def _default_link_handler(link: RenderLink) -> str:
    target = link.target
    if link.title:
        return f'[{link.text}]({target} "{link.title}")'
    return f"[{link.text}]({target})"


def render_markdown_with_markers(
    ir: MarkdownIR, options: Optional[RenderOptions] = None
) -> str:
    if options is None:
        options = RenderOptions()

    style_map = options.style_map
    link_handler = options.link_handler or _default_link_handler

    text = ir.text
    if not text:
        return ""

    style_events: List[tuple] = []
    for span in ir.styles:
        marker = _get_style_marker(span.style, style_map)
        if marker is None:
            continue
        style_events.append((span.start, "open", span.style, marker, span))
        style_events.append((span.end, "close", span.style, marker, span))

    for link in ir.links:
        style_events.append((link.start, "link_open", "link", None, link))
        style_events.append((link.end, "link_close", "link", None, link))

    style_events.sort(key=lambda e: (e[0], 0 if e[1] == "close" else 1))

    result_parts: List[str] = []
    prev_pos = 0

    active_styles: List[tuple] = []
    active_links: List[MarkdownLinkSpan] = []

    for pos, event_type, style, marker, span_data in style_events:
        result_parts.append(text[prev_pos:pos])

        if event_type == "open" and marker is not None:
            result_parts.append(marker.open)
            active_styles.append((style, marker))
        elif event_type == "close" and marker is not None:
            if active_styles:
                active_styles.pop()
            result_parts.append(marker.close)
        elif event_type == "link_open":
            if isinstance(span_data, MarkdownLinkSpan):
                link_text = text[span_data.text_start : span_data.text_end]
                rendered = link_handler(
                    RenderLink(
                        target=span_data.target,
                        title=span_data.title,
                        text=link_text,
                    )
                )
                result_parts.append(rendered)
        elif event_type == "link_close":
            pass

        prev_pos = pos

    result_parts.append(text[prev_pos:])

    return "".join(result_parts)


def build_default_style_map() -> RenderStyleMap:
    return RenderStyleMap(
        bold=RenderStyleMarker(style="bold", open="**", close="**"),
        italic=RenderStyleMarker(style="italic", open="*", close="*"),
        underline=RenderStyleMarker(style="underline", open="<u>", close="</u>"),
        strikethrough=RenderStyleMarker(style="strikethrough", open="~~", close="~~"),
        code=RenderStyleMarker(style="code", open="`", close="`"),
        link=RenderStyleMarker(style="link", open="[", close="]"),
        image=RenderStyleMarker(style="image", open="![", close="]"),
        inline_html=RenderStyleMarker(style="inline_html", open="", close=""),
        inline_math=RenderStyleMarker(style="inline_math", open="$", close="$"),
        display_math=RenderStyleMarker(style="display_math", open="$$", close="$$"),
        footnote=RenderStyleMarker(style="footnote", open="[^", close="]"),
        highlight=RenderStyleMarker(style="highlight", open="==", close="=="),
        subscript=RenderStyleMarker(style="subscript", open="<sub>", close="</sub>"),
        superscript=RenderStyleMarker(style="superscript", open="<sup>", close="</sup>"),
        ruby=RenderStyleMarker(style="ruby", open="<ruby>", close="</ruby>"),
    )


def render_plain(ir: MarkdownIR) -> str:
    return ir.text


def render_with_style(
    ir: MarkdownIR, style_map: RenderStyleMap
) -> str:
    return render_markdown_with_markers(
        ir, RenderOptions(style_map=style_map)
    )