"""Shared terminal output formatting helpers for daemon install/control commands.

Mirrors src/daemon/output.ts. Terminal colorization is stubbed (plain text)
since the terminal-core theme package is not yet ported.
"""

from __future__ import annotations

import io
from typing import Any, Iterable


def to_posix_path(value: str) -> str:
    """Normalize Windows separators for command output paths."""
    return value.replace("\\", "/")


def format_line(label: str, value: str) -> str:
    """Format a labeled daemon output line with terminal-aware styling.

    Without the terminal-core theme package, outputs plain ``label: value``.
    """
    return f"{label}: {value}"


def write_formatted_lines(
    stdout: io.TextIOBase,
    lines: Iterable[dict[str, str]],
    opts: dict[str, Any] | None = None,
) -> None:
    """Write formatted lines to stdout, keeping output line-oriented for shell parsing."""
    if opts and opts.get("leadingBlankLine"):
        stdout.write("\n")
    for line in lines:
        stdout.write(f"{format_line(line['label'], line['value'])}\n")
