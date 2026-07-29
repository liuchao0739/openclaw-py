"""Gateway method/event catalog.

Mirrors src/gateway/server-methods-list.ts.
"""

from __future__ import annotations

from typing import Any

GATEWAY_EVENTS: Any = None

def list_core_gateway_methods(*args: Any, **kwargs: Any) -> Any: ...
def list_gateway_methods(*args: Any, **kwargs: Any) -> Any: ...
