from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class FinalTagMatch:
    index: int
    text: str
    is_close: bool
    is_self_closing: bool


_FINAL_TAG_CANDIDATE_RE = re.compile(r"<[^<>]*>")


def _is_whitespace(char: str) -> bool:
    return char.isspace()


def _parse_attribute_list(text: str) -> bool:
    index = 0
    n = len(text)
    while index < n:
        while index < n and _is_whitespace(text[index]):
            index += 1
        if index >= n:
            return True

        name_start = index
        while index < n:
            char = text[index]
            if _is_whitespace(char) or char == "=":
                break
            if char in ("/", '"', "'", "<", ">"):
                return False
            index += 1
        if index == name_start:
            return False

        while index < n and _is_whitespace(text[index]):
            index += 1
        if index >= n or text[index] != "=":
            continue
        index += 1
        while index < n and _is_whitespace(text[index]):
            index += 1
        if index >= n:
            return False

        quote = text[index]
        if quote in ('"', "'"):
            index += 1
            end = text.find(quote, index)
            if end == -1:
                return False
            index = end + 1
            continue

        value_start = index
        while index < n and not _is_whitespace(text[index]):
            char = text[index]
            if char in ('"', "'", "<", ">"):
                return False
            index += 1
        if index == value_start:
            return False
    return True


def _parse_final_tag(text: str) -> tuple[bool, bool] | None:
    if not text.startswith("<") or not text.endswith(">"):
        return None

    body = text[1:-1].lstrip()
    is_close = False
    if body.startswith("/"):
        is_close = True
        body = body[1:].lstrip()

    if not body.lower().startswith("final"):
        return None
    boundary = body[5] if len(body) > 5 else ""
    if boundary and not _is_whitespace(boundary) and boundary != "/":
        return None

    rest = body[5:]
    if is_close:
        return (True, False) if rest.strip() == "" else None

    trimmed_rest = rest.rstrip()
    is_self_closing = trimmed_rest.endswith("/")
    rest = trimmed_rest[:-1] if is_self_closing else rest
    if not _parse_attribute_list(rest):
        return None
    return (False, is_self_closing)


def find_final_tag_matches(text: str) -> list[FinalTagMatch]:
    matches: list[FinalTagMatch] = []
    for match in _FINAL_TAG_CANDIDATE_RE.finditer(text):
        tag_text = match.group(0)
        parsed = _parse_final_tag(tag_text)
        if parsed is None:
            continue
        is_close, is_self_closing = parsed
        matches.append(
            FinalTagMatch(
                index=match.start(),
                text=tag_text,
                is_close=is_close,
                is_self_closing=is_self_closing,
            )
        )
    return matches


def strip_final_tags(text: str) -> str:
    output: list[str] = []
    last_index = 0
    for match in find_final_tag_matches(text):
        output.append(text[last_index : match.index])
        last_index = match.index + len(match.text)
    output.append(text[last_index:])
    return "".join(output)
