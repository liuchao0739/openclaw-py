from __future__ import annotations

from typing import Any

from openclaw.commands.channels._helpers import (
    _normalize_lowercase_string_or_empty,
    _parse_strict_positive_integer,
)

DEFAULT_LIMIT = 200
MAX_BYTES = 1_000_000


def _parse_channel_filter(raw: str | None) -> str:
    trimmed = _normalize_lowercase_string_or_empty(raw)
    if not trimmed or trimmed == "all":
        return "all"
    return trimmed


def _matches_channel(line: dict[str, Any], channel: str) -> bool:
    if channel == "all":
        return True
    needle = f"gateway/channels/{channel}"
    subsystem = line.get("subsystem", "")
    if isinstance(subsystem, str) and needle in subsystem:
        return True
    module = line.get("module", "")
    if isinstance(module, str) and channel in module:
        return True
    return False


def _parse_lines_option(value: Any) -> int:
    if value is None or value == "":
        return DEFAULT_LIMIT
    parsed = _parse_strict_positive_integer(value)
    if parsed is None:
        raise ValueError("--lines must be a positive integer.")
    return parsed


def _read_tail_lines(file_path: str, limit: int) -> list[str]:
    import os
    if not os.path.exists(file_path):
        return []
    try:
        file_size = os.path.getsize(file_path)
        max_bytes = min(MAX_BYTES, file_size)
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            f.seek(max(0, file_size - MAX_BYTES))
            text = f.read()
        lines = text.split("\n")
        if lines and lines[-1] == "":
            lines = lines[:-1]
        if len(lines) > limit:
            lines = lines[-limit:]
        return lines
    except (OSError, IOError):
        return []


def _parse_log_line(line: str) -> dict[str, Any] | None:
    parts = line.split(" | ")
    if len(parts) < 1:
        return None
    result: dict[str, Any] = {"message": line}
    for part in parts:
        if "=" in part:
            key, _, value = part.partition("=")
            result[key.strip()] = value.strip()
    return result


async def channels_logs_command(
    opts: dict[str, Any],
    runtime: dict[str, Any] | None = None,
) -> None:
    rt = runtime or {}
    channel = _parse_channel_filter(opts.get("channel"))
    limit = _parse_lines_option(opts.get("lines"))

    log_file = rt.get("logFile", "openclaw.log")
    raw_lines = _read_tail_lines(log_file, limit * 4)
    parsed = [p for p in (_parse_log_line(l) for l in raw_lines) if p]
    filtered = [l for l in parsed if _matches_channel(l, channel)]
    lines = filtered[max(0, len(filtered) - limit):]

    json_output = opts.get("json", False)
    if json_output:
        if rt.get("writeJson"):
            rt["writeJson"](rt, {"file": log_file, "channel": channel, "lines": lines})
        return

    if rt.get("log"):
        rt["log"](f"Log file: {log_file}")
        if channel != "all":
            rt["log"](f"Channel: {channel}")
        if not lines:
            rt["log"]("No matching log lines.")
        for line in lines:
            ts = f"{line.get('time', '')} " if line.get("time") else ""
            level = f"{_normalize_lowercase_string_or_empty(line.get('level'))} " if line.get("level") else ""
            rt["log"](f"{ts}{level}{line.get('message', '')}".strip())
