import json
import re
from typing import Any, List, Optional


def _extract_last_json_object(raw: str) -> Any:
    trimmed = raw.strip()
    ranges: List[dict] = []
    starts: List[int] = []
    in_string = False
    escaped = False
    preamble_quote: Optional[str] = None
    preamble_escaped = False
    previous_significant: Optional[str] = None
    line_has_non_whitespace = False
    array_depth = 0
    candidate_has_content = False

    for index in range(len(trimmed)):
        character = trimmed[index]
        if in_string:
            if character in "\n\r":
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

        if len(starts) == 0:
            if preamble_quote is not None:
                if character in "\n\r":
                    preamble_quote = None
                    preamble_escaped = False
                elif preamble_escaped:
                    preamble_escaped = False
                elif character == "\\":
                    preamble_escaped = True
                elif character == preamble_quote:
                    preamble_quote = None
                continue
            if character in "\"'`":
                previous = trimmed[index - 1] if index > 0 else None
                if previous is None or re.match(r"[\s:([\{]", previous):
                    preamble_quote = character
                    preamble_escaped = False
                    continue
            if character == "{":
                array_depth = 0
                candidate_has_content = False
                starts.append(index)
            if not re.match(r"\s", character):
                previous_significant = character
                line_has_non_whitespace = True
            elif character in "\n\r":
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
                or (previous_significant == "," and (line_has_non_whitespace or array_depth > 0))
            ):
                starts.append(index)
            elif not line_has_non_whitespace and not had_candidate_content:
                starts.clear()
                starts.append(index)
                array_depth = 0
                candidate_has_content = False
        elif character == "}" and len(starts) > 0:
            start = starts.pop()
            if len(starts) == 0:
                ranges.append({"start": start, "end": index})
        elif character == "[":
            array_depth += 1
        elif character == "]" and array_depth > 0:
            array_depth -= 1

        if not re.match(r"\s", character):
            candidate_has_content = True
            previous_significant = character
            line_has_non_whitespace = True
        elif character in "\n\r":
            line_has_non_whitespace = False

    for index in range(len(ranges) - 1, -1, -1):
        r = ranges[index]
        try:
            return json.loads(trimmed[r["start"]:r["end"] + 1])
        except Exception:
            pass

    return None


def extract_gemini_response(raw: str) -> Optional[str]:
    payload = _extract_last_json_object(raw)
    if not payload or not isinstance(payload, dict):
        return None
    response = payload.get("response")
    if not isinstance(response, str):
        return None
    trimmed = response.strip()
    return trimmed or None
