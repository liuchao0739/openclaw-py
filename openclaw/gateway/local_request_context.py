"""Local embedded Gateway request context.

Mirrors src/gateway/local-request-context.ts.
"""

from __future__ import annotations

from typing import Any

def create_local_gateway_request_context(*args: Any, **kwargs: Any) -> Any: ...
def with_local_gateway_request_scope(*args: Any, **kwargs: Any) -> Any: ...
