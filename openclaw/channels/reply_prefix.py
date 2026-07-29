"""Reply-prefix context helpers shared by channel reply dispatchers.

Mirrors src/channels/reply-prefix.ts.
"""

from __future__ import annotations

from typing import Any

ReplyPrefixContextBundle = Any
ReplyPrefixOptions = Any

def create_reply_prefix_context(*args: Any, **kwargs: Any) -> Any: ...
def create_reply_prefix_options(*args: Any, **kwargs: Any) -> Any: ...
