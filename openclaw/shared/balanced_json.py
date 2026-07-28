"""Balanced JSON fragment scanner extracts JSON objects/arrays from arbitrary text."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

JsonOpeningDelimiter = Literal["{", "["]


@dataclass
class BalancedJsonFragment:
    json: str
    start_index: int
    end_index: int


_CLOSING_DELIMITER: dict[str, str] = {"{": "}", "[": "]"}


def _is_json_opening_delimiter(char: str, openers: list[str]) -> bool:
    return char == "{" and "{" in openers or char == "[" and "[" in openers


def extract_balanced_json_prefix(
    raw: str,
    openers: list[str] | None = None,
) -> BalancedJsonFragment | None:
    if openers is None:
        openers = ["{", "["]
    start = 0
    while start < len(raw) and not _is_json_opening_delimiter(raw[start], openers):
        start += 1
    if start >= len(raw):
        return None

    stack: list[str] = []
    in_string = False
    escaped = False
    for i in range(start, len(raw)):
        char = raw[i]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
            continue
        if _is_json_opening_delimiter(char, openers):
            stack.append(char)
            continue
        opener = stack[-1] if stack else None
        if opener and char == _CLOSING_DELIMITER.get(opener, ""):
            stack.pop()
            if len(stack) == 0:
                return BalancedJsonFragment(
                    json=raw[start : i + 1],
                    start_index=start,
                    end_index=i,
                )
    return None


def extract_balanced_json_fragments(
    raw: str,
    openers: list[str] | None = None,
) -> list[BalancedJsonFragment]:
    fragments: list[BalancedJsonFragment] = []
    offset = 0
    while offset < len(raw):
        fragment = extract_balanced_json_prefix(raw[offset:], openers)
        if not fragment:
            break
        fragments.append(
            BalancedJsonFragment(
                json=fragment.json,
                start_index=offset + fragment.start_index,
                end_index=offset + fragment.end_index,
            )
        )
        offset += fragment.end_index + 1
    return fragments
