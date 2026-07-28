from __future__ import annotations

import re

from .code_regions import CodeRegion, find_code_regions, is_inside_code

_MODEL_SPECIAL_TOKEN_RE = re.compile(r"<[|｜][^|｜]*[|｜]>")


def _overlaps_code_region(
    start: int,
    end: int,
    code_regions: list[CodeRegion],
) -> bool:
    return any(start < r.end and end > r.start for r in code_regions)


def _should_insert_separator(before: str | None, after: str | None) -> bool:
    return bool(before and after and not before.isspace() and not after.isspace())


def strip_model_special_tokens(text: str) -> str:
    if not text:
        return text
    if not _MODEL_SPECIAL_TOKEN_RE.search(text):
        return text

    code_regions = find_code_regions(text)
    out: list[str] = []
    cursor = 0
    for match in _MODEL_SPECIAL_TOKEN_RE.finditer(text):
        matched = match.group(0)
        start = match.start()
        end = start + len(matched)
        out.append(text[cursor:start])
        if is_inside_code(start, code_regions) or _overlaps_code_region(
            start, end, code_regions
        ):
            out.append(matched)
        elif _should_insert_separator(
            text[start - 1] if start > 0 else None,
            text[end] if end < len(text) else None,
        ):
            out.append(" ")
        cursor = end
    out.append(text[cursor:])
    return "".join(out)
