"""Log tail helpers read recent log lines with optional parsing and redaction.

Mirrors src/logging/log-tail.ts.
"""

from __future__ import annotations

import os
import re
from typing import Any

from openclaw.logging.redact import redact_sensitive_lines, resolve_redact_options

DEFAULT_LIMIT = 500
DEFAULT_MAX_BYTES = 250000
MAX_LIMIT = 5000
MAX_BYTES = 1000000
ROLLING_LOG_RE = re.compile(r"^openclaw-\d{4}-\d{2}-\d{2}\.log$")


def _clamp(value: int, min_value: int, max_value: int) -> int:
    return max(min_value, min(max_value, value))


def _is_rolling_log_file(file_path: str) -> bool:
    return bool(ROLLING_LOG_RE.match(os.path.basename(file_path)))


def resolve_log_file(file_path: str) -> str:
    if os.path.exists(file_path):
        return file_path
    if not _is_rolling_log_file(file_path):
        return file_path
    dir_path = os.path.dirname(file_path)
    try:
        entries = os.listdir(dir_path)
    except OSError:
        return file_path
    candidates = []
    for name in entries:
        if not ROLLING_LOG_RE.match(name):
            continue
        full_path = os.path.join(dir_path, name)
        try:
            stat = os.stat(full_path)
            candidates.append((full_path, stat.st_mtime))
        except OSError:
            continue
    candidates.sort(key=lambda c: c[1], reverse=True)
    return candidates[0][0] if candidates else file_path


def _read_log_slice(params: dict[str, Any]) -> dict[str, Any]:
    file_path = params["file"]
    try:
        stat = os.stat(file_path)
    except OSError:
        return {"cursor": 0, "size": 0, "lines": [], "truncated": False, "reset": False}
    size = stat.st_size
    max_bytes = _clamp(params.get("maxBytes", DEFAULT_MAX_BYTES), 1, MAX_BYTES)
    limit = _clamp(params.get("limit", DEFAULT_LIMIT), 1, MAX_LIMIT)
    cursor = params.get("cursor")
    reset = False
    truncated = False
    if cursor is not None:
        if cursor > size:
            reset = True
            start = max(0, size - max_bytes)
            truncated = start > 0
        else:
            start = cursor
            if size - start > max_bytes:
                reset = True
                truncated = True
                start = max(0, size - max_bytes)
    else:
        start = max(0, size - max_bytes)
        truncated = start > 0
    if size == 0 or size <= start:
        return {"cursor": size, "size": size, "lines": [], "truncated": truncated, "reset": reset}
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            f.seek(start)
            text = f.read(max_bytes)
    except OSError:
        return {"cursor": size, "size": size, "lines": [], "truncated": truncated, "reset": reset}
    lines = text.split("\n")
    if start > 0:
        lines = lines[1:]
    if lines and lines[-1] == "":
        lines = lines[:-1]
    if len(lines) > limit:
        lines = lines[-limit:]
    return {"cursor": size, "size": size, "lines": lines, "truncated": truncated, "reset": reset}


def read_configured_log_tail(params: dict[str, Any] | None = None) -> dict[str, Any]:
    from openclaw.logging.log_file_path import resolve_configured_log_file_path
    file_path = resolve_log_file(resolve_configured_log_file_path())
    result = _read_log_slice(
        {
            "file": file_path,
            "cursor": (params or {}).get("cursor"),
            "limit": (params or {}).get("limit", DEFAULT_LIMIT),
            "maxBytes": (params or {}).get("maxBytes", DEFAULT_MAX_BYTES),
        }
    )
    redaction = resolve_redact_options()
    return {
        "file": file_path,
        **result,
        "lines": redact_sensitive_lines(result["lines"], redaction),
    }


__all__ = ["resolve_log_file", "read_configured_log_tail"]
