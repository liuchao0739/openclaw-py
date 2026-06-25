"""Bash tools configuration and constants."""

from __future__ import annotations

from typing import Literal

BashExecutionMode = Literal["sequential", "parallel"]

DEFAULT_BASH_TIMEOUT_MS = 120_000
MAX_BASH_OUTPUT_CHARS = 30_000
MAX_BASH_STDERR_LINES = 500

BASH_TOOL_NAME = "bash"
EXEC_TOOL_NAME = "exec"

# Commands that are always allowed without approval
SAFE_COMMANDS = frozenset({
    "ls", "pwd", "echo", "cat", "head", "tail", "wc", "sort", "uniq",
    "grep", "find", "which", "file", "stat", "date", "whoami", "env",
    "git status", "git log", "git diff", "git branch",
})
