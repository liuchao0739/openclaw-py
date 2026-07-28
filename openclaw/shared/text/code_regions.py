from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class CodeRegion:
    start: int
    end: int


_FENCED_RE = re.compile(r"(?:^|\n)(```|~~~)[^\n]*\n[\s\S]*?(?:\n\1|$)")
_INLINE_RE = re.compile(r"`+[^`]+`+")


def find_code_regions(text: str) -> list[CodeRegion]:
    regions: list[CodeRegion] = []

    for match in _FENCED_RE.finditer(text):
        start = match.start() + (1 if match.group(0)[0] in ("\n", "\r") else 0)
        full = match.group(0)
        prefix_len = len(full) - len(full.lstrip("\r\n"))
        start = match.start() + prefix_len
        end = start + len(full) - prefix_len
        regions.append(CodeRegion(start=start, end=end))

    for match in _INLINE_RE.finditer(text):
        start = match.start()
        end = start + len(match.group(0))
        inside_fenced = any(r.start <= start and end <= r.end for r in regions)
        if not inside_fenced:
            regions.append(CodeRegion(start=start, end=end))

    regions.sort(key=lambda r: r.start)
    return regions


def is_inside_code(pos: int, regions: list[CodeRegion]) -> bool:
    return any(r.start <= pos < r.end for r in regions)
