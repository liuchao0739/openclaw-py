"""Canonical conversation resolution for command and inbound channel flows.

Mirrors src/channels/conversation-resolution.ts.
"""

from __future__ import annotations

from typing import Any

ResolveCommandConversationResolutionInput = Any

def resolve_channel_default_binding_placement(*args: Any, **kwargs: Any) -> Any: ...
def resolve_command_conversation_resolution(*args: Any, **kwargs: Any) -> Any: ...
def resolve_inbound_conversation_resolution(*args: Any, **kwargs: Any) -> Any: ...
