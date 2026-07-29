"""Log line parsing helpers convert text log entries into structured records.

Mirrors src/logging/parse-log-line.ts.
"""

from __future__ import annotations

import json
from typing import Any


def _extract_message(value: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in value:
        if not key.isdigit():
            continue
        item = value[key]
        if isinstance(item, str):
            parts.append(item)
        elif item is not None:
            parts.append(json.dumps(item))
    return " ".join(parts)


def _parse_meta_name(raw: Any) -> dict[str, str | None]:
    if not isinstance(raw, str):
        return {}
    try:
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            return {}
        return {
            "subsystem": parsed["subsystem"] if isinstance(parsed.get("subsystem"), str) else None,
            "module": parsed["module"] if isinstance(parsed.get("module"), str) else None,
        }
    except Exception:
        return {}


def parse_log_line(raw: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            return None
        meta = parsed.get("_meta")
        meta = meta if isinstance(meta, dict) else None
        name_meta = _parse_meta_name(meta.get("name") if meta else None)
        level_raw = meta.get("logLevelName") if meta else None
        level_raw = level_raw if isinstance(level_raw, str) else None
        time_value = parsed.get("time")
        time_value = time_value if isinstance(time_value, str) else None
        if time_value is None and meta:
            date_value = meta.get("date")
            time_value = date_value if isinstance(date_value, str) else None
        return {
            "time": time_value,
            "level": level_raw.lower() if level_raw else None,
            "subsystem": name_meta.get("subsystem"),
            "module": name_meta.get("module"),
            "message": _extract_message(parsed),
            "raw": raw,
        }
    except Exception:
        return None


__all__ = ["parse_log_line"]
