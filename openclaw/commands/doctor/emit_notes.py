"""Doctor note emission helpers that sanitize user-visible repair output."""

from __future__ import annotations

import re
from typing import Any, Callable

_ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


def _sanitize_for_log(text: str) -> str:
    """Strip terminal control sequences from text."""
    return _ANSI_RE.sub("", text)


def sanitize_doctor_note(note: str) -> str:
    """Strip terminal control sequences from a potentially multi-line doctor note."""
    return "\n".join(_sanitize_for_log(line) for line in note.split("\n"))


def emit_doctor_notes(
    note_fn: Callable[..., None],
    change_notes: list[str] | None = None,
    info_notes: list[str] | None = None,
    warning_notes: list[str] | None = None,
) -> None:
    """Emit grouped doctor change, info, and warning notes with sanitized content."""
    for change in change_notes or []:
        note_fn(sanitize_doctor_note(change), "Doctor changes")
    for info in info_notes or []:
        note_fn(sanitize_doctor_note(info), "Doctor info")
    for warning in warning_notes or []:
        note_fn(sanitize_doctor_note(warning), "Doctor warnings")
