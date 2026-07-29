"""Gateway chat attachment parser.

Mirrors src/gateway/chat-attachments.ts.
"""

from __future__ import annotations

from typing import Any

DEFAULT_CHAT_ATTACHMENT_MAX_MB: Any = None

ChatAttachment = Any
ChatImageContent = Any
OffloadedRef = Any

class UnsupportedAttachmentError: ...
class MediaOffloadError: ...

def resolve_chat_attachment_max_bytes(*args: Any, **kwargs: Any) -> Any: ...
async def parse_message_with_attachments(*args: Any, **kwargs: Any) -> Any: ...
