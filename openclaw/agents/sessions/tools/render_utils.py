"""Rendering helpers for session tool output.

Normalizes paths/text before tool results are styled or truncated.
The TUI-specific rendering (image fallbacks, theme) is deferred until the
TUI layer is ported.
"""

from __future__ import annotations

import os
import re
from typing import Any


def shorten_path(path: Any) -> str:
    """Shorten paths under the current home directory for display."""
    if not isinstance(path, str):
        return ""
    home = os.path.expanduser("~")
    if path.startswith(home):
        return f"~{path[len(home):]}"
    return path


def str_value(value: Any) -> str | None:
    """Return a display string for string/nullish values, or None for unsupported."""
    if isinstance(value, str):
        return value
    if value is None:
        return ""
    return None


def replace_tabs(text: str) -> str:
    """Replace tabs with stable spaces so terminal layout does not shift."""
    return text.replace("\t", "   ")


def normalize_display_text(text: str) -> str:
    """Normalize raw terminal output before display."""
    return text.replace("\r", "")


_ANSI_ESCAPE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


def strip_ansi(text: str) -> str:
    """Strip ANSI escape sequences from text."""
    return _ANSI_ESCAPE.sub("", text)


def get_text_output(
    result: dict[str, Any] | None,
    show_images: bool = False,
) -> str:
    """Extract text output from a tool result."""
    if not result:
        return ""

    content = result.get("content", [])
    text_blocks = [c for c in content if isinstance(c, dict) and c.get("type") == "text"]

    output = "\n".join(
        normalize_display_text(strip_ansi(c.get("text", ""))) for c in text_blocks
    )

    return output
