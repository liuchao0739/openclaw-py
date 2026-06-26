"""Agent harness package — errors, hook history."""

from .errors import MissingAgentHarnessError, is_missing_agent_harness_error
from .hook_history import (
    MAX_AGENT_HOOK_HISTORY_MESSAGES,
    limit_agent_hook_history_messages,
    build_agent_hook_conversation_messages,
)

__all__ = [
    "MissingAgentHarnessError",
    "is_missing_agent_harness_error",
    "MAX_AGENT_HOOK_HISTORY_MESSAGES",
    "limit_agent_hook_history_messages",
    "build_agent_hook_conversation_messages",
]
