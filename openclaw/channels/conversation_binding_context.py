"""Conversation-binding key resolver shared by plugin commands and reply/session actions.

Mirrors src/channels/conversation-binding-context.ts.
"""

from __future__ import annotations

from typing import Any

def resolve_conversation_binding_context(*args: Any, **kwargs: Any) -> Any: ...
