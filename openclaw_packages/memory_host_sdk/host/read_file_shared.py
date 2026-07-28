from __future__ import annotations

from typing import Optional


DEFAULT_MEMORY_READ_LINES = 120
DEFAULT_MEMORY_READ_MAX_CHARS = 12_000


def _build_continuation_notice(next_from: Optional[int], suggest_read_fallback: Optional[bool] = None) -> str:
    if isinstance(next_from, int):
        base = f"[More content available. Use from={next_from} to continue.]"
    else:
        base = "[More content available. Requested excerpt exceeded the default maxChars budget.]"
    fallback = " If you need the full raw line, use read on the source file." if suggest_read_fallback else ""
    return f"\n\n{base[:-1]}{fallback}]"


def _fit_lines_to_char_budget(lines: list, max_chars: int) -> dict:
    if not lines:
        return {"text": "", "includedLines": 0, "hardTruncatedSingleLine": False}

    included_lines = len(lines)
    text = "\n".join(lines)
    while included_lines > 1 and len(text) > max_chars:
        included_lines -= 1
        text = "\n".join(lines[:included_lines])

    if len(text) <= max_chars:
        return {"text": text, "includedLines": included_lines, "hardTruncatedSingleLine": False}

    return {
        "text": text[:max_chars],
        "includedLines": 1,
        "hardTruncatedSingleLine": True,
    }


def _normalize_positive_integer(value: Optional[float], fallback: int) -> int:
    if isinstance(value, (int, float)) and value == value and value > 0:
        return max(1, int(value))
    return fallback


def build_memory_read_result_from_slice(
    selected_lines: list,
    rel_path: str,
    start_line: int,
    more_source_lines_remain: Optional[bool] = None,
    max_chars: Optional[int] = None,
    suggest_read_fallback: Optional[bool] = None,
) -> dict:
    start = _normalize_positive_integer(start_line, 1)
    fitted = _fit_lines_to_char_budget(
        lines=selected_lines,
        max_chars=_normalize_positive_integer(max_chars, DEFAULT_MEMORY_READ_MAX_CHARS),
    )
    more_source = more_source_lines_remain or False
    char_cap_truncated = fitted["hardTruncatedSingleLine"] or fitted["includedLines"] < len(selected_lines)
    next_from = None
    if not fitted["hardTruncatedSingleLine"] and (more_source or fitted["includedLines"] < len(selected_lines)):
        next_from = start + fitted["includedLines"]
    truncated = char_cap_truncated or more_source
    text = fitted["text"]
    if truncated and text:
        text += _build_continuation_notice(
            next_from,
            suggest_read_fallback=fitted["hardTruncatedSingleLine"] and suggest_read_fallback,
        )
    result = {
        "text": text,
        "path": rel_path,
        "from": start,
        "lines": fitted["includedLines"],
    }
    if truncated:
        result["truncated"] = True
    if isinstance(next_from, int):
        result["nextFrom"] = next_from
    return result


def build_memory_read_result(
    content: str,
    rel_path: str,
    from_line: Optional[int] = None,
    lines: Optional[int] = None,
    default_lines: Optional[int] = None,
    max_chars: Optional[int] = None,
    suggest_read_fallback: Optional[bool] = None,
) -> dict:
    file_lines = content.split("\n")
    start = _normalize_positive_integer(from_line, 1)
    requested_count = _normalize_positive_integer(
        lines if lines is not None else default_lines,
        DEFAULT_MEMORY_READ_LINES,
    )
    selected_lines = file_lines[start - 1:start - 1 + requested_count]
    more_source_remain = start - 1 + len(selected_lines) < len(file_lines)
    return build_memory_read_result_from_slice(
        selected_lines=selected_lines,
        rel_path=rel_path,
        start_line=start,
        more_source_lines_remain=more_source_remain,
        max_chars=max_chars,
        suggest_read_fallback=suggest_read_fallback,
    )
