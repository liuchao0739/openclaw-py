"""Gateway agent prompt builder.

Mirrors src/gateway/agent-prompt.ts.
"""

from __future__ import annotations

from typing import Any

IMAGE_ONLY_USER_MESSAGE: Any = None

ConversationEntry = Any

def build_agent_message_from_conversation_entries(*args: Any, **kwargs: Any) -> Any: ...
