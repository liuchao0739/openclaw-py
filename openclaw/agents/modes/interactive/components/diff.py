from __future__ import annotations

import re
import difflib
from typing import Any

from openclaw.agents.modes.interactive.theme.theme import theme


def _parse_diff_line(line: str) -> dict[str, str] | None:
    m = re.match(r"^([+\-\s])(\s*\d*)\s(.*)$", line)
    if not m:
        return None
    return {"prefix": m.group(1), "lineNum": m.group(2), "content": m.group(3)}


def _replace_tabs(text: str) -> str:
    return text.replace("\t", "   ")


def _render_intra_line_diff(
    old_content: str, new_content: str
) -> tuple[str, str]:
    old_words = old_content.split()
    new_words = new_content.split()

    sm = difflib.SequenceMatcher(None, old_words, new_words)
    removed_line = ""
    added_line = ""
    is_first_removed = True
    is_first_added = True

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "replace" or tag == "delete":
            removed_val = " ".join(old_words[i1:i2])
            if is_first_removed:
                leading_ws = old_content[: len(old_content) - len(old_content.lstrip())]
                removed_val = removed_val[len(leading_ws):] if removed_val.startswith(leading_ws) else removed_val
                removed_line += leading_ws
                is_first_removed = False
            if removed_val:
                removed_line += theme.inverse(removed_val)

        if tag == "replace" or tag == "insert":
            added_val = " ".join(new_words[j1:j2])
            if is_first_added:
                leading_ws = new_content[: len(new_content) - len(new_content.lstrip())]
                added_val = added_val[len(leading_ws):] if added_val.startswith(leading_ws) else added_val
                added_line += leading_ws
                is_first_added = False
            if added_val:
                added_line += theme.inverse(added_val)

        if tag == "equal":
            segment = " ".join(old_words[i1:i2])
            removed_line += segment
            added_line += segment

    return removed_line, added_line


def render_diff(diff_text: str, _options: dict[str, Any] | None = None) -> str:
    lines = diff_text.split("\n")
    result: list[str] = []

    i = 0
    while i < len(lines):
        line = lines[i]
        parsed = _parse_diff_line(line)

        if not parsed:
            result.append(theme.fg("toolDiffContext", line))
            i += 1
            continue

        if parsed["prefix"] == "-":
            removed_lines: list[dict[str, str]] = []
            while i < len(lines):
                p = _parse_diff_line(lines[i])
                if not p or p["prefix"] != "-":
                    break
                removed_lines.append({"lineNum": p["lineNum"], "content": p["content"]})
                i += 1

            added_lines: list[dict[str, str]] = []
            while i < len(lines):
                p = _parse_diff_line(lines[i])
                if not p or p["prefix"] != "+":
                    break
                added_lines.append({"lineNum": p["lineNum"], "content": p["content"]})
                i += 1

            if len(removed_lines) == 1 and len(added_lines) == 1:
                removed = removed_lines[0]
                added = added_lines[0]
                removed_line, added_line = _render_intra_line_diff(
                    _replace_tabs(removed["content"]),
                    _replace_tabs(added["content"]),
                )
                result.append(theme.fg("toolDiffRemoved", f"-{removed['lineNum']} {removed_line}"))
                result.append(theme.fg("toolDiffAdded", f"+{added['lineNum']} {added_line}"))
            else:
                for removed in removed_lines:
                    result.append(
                        theme.fg("toolDiffRemoved", f"-{removed['lineNum']} {_replace_tabs(removed['content'])}")
                    )
                for added in added_lines:
                    result.append(
                        theme.fg("toolDiffAdded", f"+{added['lineNum']} {_replace_tabs(added['content'])}")
                    )
        elif parsed["prefix"] == "+":
            result.append(
                theme.fg("toolDiffAdded", f"+{parsed['lineNum']} {_replace_tabs(parsed['content'])}")
            )
            i += 1
        else:
            result.append(
                theme.fg("toolDiffContext", f" {parsed['lineNum']} {_replace_tabs(parsed['content'])}")
            )
            i += 1

    return "\n".join(result)
