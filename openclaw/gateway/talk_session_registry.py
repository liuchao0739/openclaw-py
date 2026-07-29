"""Process-local registry that lets Talk protocol methods resolve opaque

Mirrors src/gateway/talk-session-registry.ts.
"""

from __future__ import annotations

from typing import Any

UnifiedTalkSessionRecord = Any

def remember_unified_talk_session(*args: Any, **kwargs: Any) -> Any: ...
def get_unified_talk_session(*args: Any, **kwargs: Any) -> Any: ...
def forget_unified_talk_session(*args: Any, **kwargs: Any) -> Any: ...
def require_unified_talk_session_conn(*args: Any, **kwargs: Any) -> Any: ...
