"""Output extractors for media-understanding provider CLI responses."""

from __future__ import annotations

import json
import re


def _extract_last_json_object(raw: str) -> object | None:
    trimmed = raw.strip()
    ranges: list[tuple[int, int]] = []
    starts: list[int] = []
    in_string = False
    escaped = False
    preamble_quote: str | None = None
    preamble_escaped = False
    previous_significant: str | None = None
    line_has_non_whitespace = False
    array_depth = 0
    candidate_has_content = False

    for index, character in enumerate(trimmed):
        if in_string:
            if character in ("\n", "\r"):
                starts.clear()
                in_string = False
                escaped = False
            elif escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue

        if not starts:
            if preamble_quote is not None:
                if character in ("\n", "\r"):
                    preamble_quote = None
                    preamble_escaped = False
                elif preamble_escaped:
                    preamble_escaped = False
                elif character == "\\":
                    preamble_escaped = True
                elif character == preamble_quote:
                    preamble_quote = None
                continue
            if character in ('"', "'", "`"):
                previous = trimmed[index - 1] if index > 0 else None
                if previous is None or re.search(r"[\s:([{]", previous):
                    preamble_quote = character
                    preamble_escaped = False
                    continue
            if character == "{":
                array_depth = 0
                candidate_has_content = False
                starts.append(index)
            if not character.isspace():
                previous_significant = character
                line_has_non_whitespace = True
            elif character in ("\n", "\r"):
                line_has_non_whitespace = False
            continue

        had_candidate_content = candidate_has_content
        if character == '"':
            in_string = True
        elif character == "{":
            if (
                previous_significant == ":"
                or previous_significant == "["
                or previous_significant == '"'
                or (
                    previous_significant == ","
                    and (line_has_non_whitespace or array_depth > 0)
                )
            ):
                starts.append(index)
            elif not line_has_non_whitespace and not had_candidate_content:
                starts[:] = [index]
                array_depth = 0
                candidate_has_content = False
        elif character == "}" and starts:
            start = starts.pop()
            if not starts:
                ranges.append((start, index))
        elif character == "[":
            array_depth += 1
        elif character == "]" and array_depth > 0:
            array_depth -= 1

        if not character.isspace():
            candidate_has_content = True
            previous_significant = character
            line_has_non_whitespace = True
        elif character in ("\n", "\r"):
            line_has_non_whitespace = False

    for start, end in reversed(ranges):
        try:
            return json.loads(trimmed[start : end + 1])
        except json.JSONDecodeError:
            continue

    return None


def extract_gemini_response(raw: str) -> str | None:
    """Extract Gemini CLI-style response text from the last JSON object in output."""
    payload = _extract_last_json_object(raw)
    if not isinstance(payload, dict):
        return None
    response = payload.get("response")
    if not isinstance(response, str):
        return None
    trimmed = response.strip()
    return trimmed or None
