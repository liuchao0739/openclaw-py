"""Queue directive parsing for /steer, /followup, /collect, /interrupt."""

from __future__ import annotations

import re
from typing import Any

from openclaw.auto_reply.reply.queue.types import QueueMode

_QUEUE_DIRECTIVE_PATTERN = re.compile(
    r"(?:^|\s)/(steer|followup|collect|interrupt)(?=$|\s)", re.IGNORECASE
)

_MODE_ALIASES: dict[str, QueueMode] = {
    "steer": "steer",
    "followup": "followup",
    "collect": "collect",
    "interrupt": "interrupt",
    "next": "followup",
    "queue": "collect",
    "cancel": "interrupt",
}


def extract_queue_directive(body: str | None) -> dict[str, Any]:
    """Extract a queue mode directive from message text.

    Returns a dict with:
    - ``mode``: the resolved QueueMode or None
    - ``cleaned``: the message text with the directive removed
    - ``hasDirective``: whether a directive was found
    """
    if not body:
        return {"mode": None, "cleaned": "", "hasDirective": False}

    match = _QUEUE_DIRECTIVE_PATTERN.search(body)
    if not match:
        return {"mode": None, "cleaned": body.strip(), "hasDirective": False}

    raw_mode = match.group(1).lower()
    mode = _MODE_ALIASES.get(raw_mode)

    if mode is None:
        return {"mode": None, "cleaned": body.strip(), "hasDirective": False}

    start = match.start() + match.group().index("/")
    end = match.end()
    cleaned = (body[:start] + " " + body[end:]).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)

    return {"mode": mode, "cleaned": cleaned, "hasDirective": True}


def resolve_queue_mode(text: str | None, default: QueueMode = "followup") -> QueueMode:
    """Resolve the queue mode from message text, falling back to default."""
    result = extract_queue_directive(text)
    return result["mode"] or default
