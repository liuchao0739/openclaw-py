"""Gateway live chat projector.

Mirrors src/gateway/live-chat-projector.ts.
"""

from __future__ import annotations

from typing import Any

MAX_LIVE_CHAT_BUFFER_CHARS: Any = None

def resolve_merged_assistant_text(*args: Any, **kwargs: Any) -> Any: ...
def normalize_live_assistant_event_text(*args: Any, **kwargs: Any) -> Any: ...
def project_live_assistant_buffered_text(*args: Any, **kwargs: Any) -> Any: ...
def should_suppress_assistant_event_for_live_chat(*args: Any, **kwargs: Any) -> Any: ...
