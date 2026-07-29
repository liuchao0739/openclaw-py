"""Active session shutdown tracker.

Mirrors src/gateway/active-sessions-shutdown-tracker.ts.
"""

from __future__ import annotations

from typing import Any

ActiveSessionForShutdown = Any

def note_active_session_for_shutdown(*args: Any, **kwargs: Any) -> Any: ...
def forget_active_session_for_shutdown(*args: Any, **kwargs: Any) -> Any: ...
def list_active_sessions_for_shutdown(*args: Any, **kwargs: Any) -> Any: ...
def clear_active_sessions_for_shutdown_tracker(*args: Any, **kwargs: Any) -> Any: ...
