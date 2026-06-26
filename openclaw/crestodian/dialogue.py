"""Crestodian dialogue helpers: parse direct commands and format approval prompts.

Mirrors src/crestodian/dialogue.ts. Only the pure helpers (approval_question,
is_yes, should_ask_assistant) are ported here; the async ``resolveCrestodianOperation``
requires the operations/overview/assistant modules which are deferred.
"""

from __future__ import annotations

import re
from typing import Any

_YES_PATTERN = re.compile(r"^(y|yes|apply|do it|approved?)$", re.IGNORECASE)


def approval_question(operation: Any) -> str:
    """Format the interactive approval prompt for a persistent operation.

    Uses the operation's ``description`` if available, else its ``kind``.
    """
    desc = getattr(operation, "description", None)
    if desc is None and isinstance(operation, dict):
        desc = operation.get("description") or operation.get("summary")
    if desc is None:
        desc = getattr(operation, "kind", "operation")
    return f"Apply this operation: {desc}?"


def is_yes(input: str) -> bool:
    """Parse affirmative approval text accepted by the interactive dialogue."""
    return bool(_YES_PATTERN.match(input.strip()))


def should_ask_assistant(input: str, operation: Any) -> bool:
    """Return True if the assistant planner should be consulted.

    The assistant is only consulted for non-empty text that did not parse into a
    known operation (kind == "none"), excluding ``quit``/``exit``.
    """
    kind = getattr(operation, "kind", None)
    if kind is None and isinstance(operation, dict):
        kind = operation.get("kind")
    if kind != "none":
        return False
    trimmed = input.strip().lower()
    if not trimmed or trimmed in ("quit", "exit"):
        return False
    return True
