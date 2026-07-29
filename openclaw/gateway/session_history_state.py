"""Gateway session-history projection state.

Mirrors src/gateway/session-history-state.ts.
"""

from __future__ import annotations

from typing import Any

class SessionHistorySseState: ...

def resolve_session_history_tail_read_options(*args: Any, **kwargs: Any) -> Any: ...
def build_session_history_snapshot(*args: Any, **kwargs: Any) -> Any: ...
