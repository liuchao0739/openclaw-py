"""Gateway session event broadcaster.

Mirrors src/gateway/server-session-events.ts.
"""

from __future__ import annotations

from typing import Any

def create_transcript_update_broadcast_handler(*args: Any, **kwargs: Any) -> Any: ...
def create_lifecycle_event_broadcast_handler(*args: Any, **kwargs: Any) -> Any: ...
