"""Parses daemon runtime command output into normalized key-value maps.

Mirrors src/daemon/runtime-parse.ts.
"""

from __future__ import annotations

import re


def _normalize_lowercase_string_or_empty(value: str) -> str:
    if isinstance(value, str):
        return value.strip().lower()
    return ""


def parse_key_value_output(output: str, separator: str) -> dict[str, str]:
    """Parse command output key-value lines using a caller-supplied separator."""
    entries: dict[str, str] = {}
    for raw_line in re.split(r"\r?\n", output):
        line = raw_line.strip()
        if not line:
            continue
        idx = line.find(separator)
        if idx <= 0:
            continue
        key = _normalize_lowercase_string_or_empty(line[:idx])
        if not key:
            continue
        value = line[idx + len(separator):].strip()
        entries[key] = value
    return entries
