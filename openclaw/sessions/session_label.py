"""User-editable session labels.

Mirrors src/sessions/session-label.ts.
"""

from __future__ import annotations

from typing import Any, Literal, TypedDict

SESSION_LABEL_MAX_LENGTH = 512


class ParsedSessionLabelOk(TypedDict):
    ok: Literal[True]
    label: str


class ParsedSessionLabelErr(TypedDict):
    ok: Literal[False]
    error: str


def parse_session_label(raw: Any) -> dict[str, Any]:
    """Parse a user-editable session label.

    Returns ``{"ok": True, "label": str}`` or ``{"ok": False, "error": str}``.
    """
    if not isinstance(raw, str):
        return {"ok": False, "error": "invalid label: must be a string"}
    trimmed = raw.strip()
    if not trimmed:
        return {"ok": False, "error": "invalid label: empty"}
    if len(trimmed) > SESSION_LABEL_MAX_LENGTH:
        return {"ok": False, "error": f"invalid label: too long (max {SESSION_LABEL_MAX_LENGTH})"}
    return {"ok": True, "label": trimmed}
