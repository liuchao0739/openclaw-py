"""Gateway pending node-work queue.

Mirrors src/gateway/node-pending-work.ts.
"""

from __future__ import annotations

from typing import Any

NodePendingWorkType = Any
NodePendingWorkPriority = Any

def enqueue_node_pending_work(*args: Any, **kwargs: Any) -> Any: ...
def drain_node_pending_work(*args: Any, **kwargs: Any) -> Any: ...
def reset_node_pending_work_for_tests(*args: Any, **kwargs: Any) -> Any: ...
def get_node_pending_work_state_count_for_tests(*args: Any, **kwargs: Any) -> Any: ...
