"""Delivery hint constants for message tool replies.

These hints guide the reply delivery system on how to handle message tool output.
"""

MESSAGE_TOOL_DELIVERY_HINTS = frozenset({
    "message_tool",
    "visible_reply",
    "source_visible",
})

MESSAGE_TOOL_ONLY_DELIVERY_HINT = "message_tool_only"

LEGACY_MESSAGE_TOOL_DELIVERY_HINTS = frozenset({
    "legacy_message_tool",
})
