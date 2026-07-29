"""Plugin-provided node.invoke policy adapter.

Mirrors src/gateway/node-invoke-plugin-policy.ts.
"""

from __future__ import annotations

from typing import Any

async def apply_plugin_node_invoke_policy(*args: Any, **kwargs: Any) -> Any: ...
