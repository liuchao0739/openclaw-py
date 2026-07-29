"""Gateway Talk relay session lifecycle helpers.

Mirrors src/gateway/talk-relay-session-lifecycle.ts.
"""

from __future__ import annotations

from typing import Any

def close_expired_talk_relay_sessions(*args: Any, **kwargs: Any) -> Any: ...
def require_active_talk_relay_session(*args: Any, **kwargs: Any) -> Any: ...
