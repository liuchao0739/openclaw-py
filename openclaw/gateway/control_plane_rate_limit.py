"""Control-plane rate limiting bounds write-side RPC attempts per device/IP and

Mirrors src/gateway/control-plane-rate-limit.ts.
"""

from __future__ import annotations

from typing import Any

testing: Any = None

def resolve_control_plane_rate_limit_key(*args: Any, **kwargs: Any) -> Any: ...
def consume_control_plane_write_budget(*args: Any, **kwargs: Any) -> Any: ...
def prune_stale_control_plane_buckets(*args: Any, **kwargs: Any) -> Any: ...
