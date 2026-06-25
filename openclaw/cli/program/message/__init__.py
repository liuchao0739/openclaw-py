"""Message CLI — command registrations and helpers."""

from openclaw.cli.program.message.helpers import MessageCliHelpers, collect_option
from openclaw.cli.program.message.register import (
    register_message_broadcast_command,
    register_message_permissions_command,
    register_message_poll_command,
    register_message_search_command,
)

__all__ = [
    "MessageCliHelpers",
    "collect_option",
    "register_message_broadcast_command",
    "register_message_permissions_command",
    "register_message_poll_command",
    "register_message_search_command",
]
