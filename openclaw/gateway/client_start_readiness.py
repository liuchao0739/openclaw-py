"""Server-side gateway client readiness adapter.

Mirrors src/gateway/client-start-readiness.ts.
"""

from __future__ import annotations

from typing import Any

def start_gateway_client_when_event_loop_ready(*args: Any, **kwargs: Any) -> Any: ...
