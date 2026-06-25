"""Reaction action message-id resolver.

Reads explicit reaction targets or falls back to the current tool message context.
"""

from __future__ import annotations

from typing import Any


def _read_string_or_number_param(params: dict[str, Any], key: str) -> str | int | None:
    """Read a string or number param, supporting snake_case aliases."""
    if key in params:
        val = params[key]
        if isinstance(val, (str, int)):
            return val
    snake_key = "".join(("_" + c.lower()) if c.isupper() else c for c in key)
    if snake_key in params:
        val = params[snake_key]
        if isinstance(val, (str, int)):
            return val
    return None


def resolve_reaction_message_id(
    args: dict[str, Any],
    tool_context: dict[str, Any] | None = None,
) -> str | int | None:
    """Resolve the message id for reaction tools from explicit args or current tool context."""
    explicit = _read_string_or_number_param(args, "messageId")
    if explicit is not None:
        return explicit
    if tool_context:
        return tool_context.get("currentMessageId")
    return None
