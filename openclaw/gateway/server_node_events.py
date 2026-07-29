"""Gateway node event dispatcher.

Mirrors src/gateway/server-node-events.ts.
"""

from __future__ import annotations

from typing import Any

handle_node_event: Any = None

NodeEventHandleResult = Any

def reset_node_event_deduplication_for_tests(*args: Any, **kwargs: Any) -> Any: ...
def get_recent_node_presence_persist_count_for_tests(*args: Any, **kwargs: Any) -> Any: ...
