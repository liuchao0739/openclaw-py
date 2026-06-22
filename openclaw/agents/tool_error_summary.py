"""Tool error summary helpers (minimal port)."""

from __future__ import annotations

import re
from typing import Literal, TypedDict

ExecLikeToolName = Literal["exec", "bash", "shell", "run", "command"]

_TOOL_NAME_PATTERN = re.compile(r"^(exec|bash|shell|run|command)(?:$|[_-])", re.I)


class ToolErrorSummary(TypedDict, total=False):
    toolName: str
    error: str
    errorCode: str
    timedOut: bool


def is_exec_like_tool_name(tool_name: str | None) -> bool:
    if not tool_name or not isinstance(tool_name, str):
        return False
    return bool(_TOOL_NAME_PATTERN.match(tool_name.strip()))