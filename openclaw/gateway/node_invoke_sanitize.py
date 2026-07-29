"""Node invocation forwarding sanitizer.

Mirrors src/gateway/node-invoke-sanitize.ts.
"""

from __future__ import annotations

from typing import Any

def sanitize_node_invoke_params_for_forwarding(*args: Any, **kwargs: Any) -> Any: ...
