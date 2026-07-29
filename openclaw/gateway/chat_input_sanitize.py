"""Chat send input sanitizer for Gateway message payloads.

Mirrors src/gateway/chat-input-sanitize.ts.
"""

from __future__ import annotations

from typing import Any

def sanitize_chat_send_message_input(*args: Any, **kwargs: Any) -> Any: ...
