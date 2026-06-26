"""ACP package — conversation id, types, secret file, commands."""

from .conversation_id import normalize_conversation_text
from .types import ACP_AGENT_INFO, normalize_acp_provenance_mode
from .secret_file import read_secret_from_file, MAX_SECRET_FILE_BYTES
from .commands import BASE_AVAILABLE_COMMANDS, get_available_commands, register_dock_command

__all__ = [
    "normalize_conversation_text",
    "ACP_AGENT_INFO",
    "normalize_acp_provenance_mode",
    "read_secret_from_file",
    "MAX_SECRET_FILE_BYTES",
    "BASE_AVAILABLE_COMMANDS",
    "get_available_commands",
    "register_dock_command",
]
