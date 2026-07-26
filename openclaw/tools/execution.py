"""Defines tool execution references used by the runtime dispatcher.

Mirrors src/tools/execution.ts.
"""

from __future__ import annotations

from openclaw.tools.types import ToolExecutorRef


def format_tool_executor_ref(ref: ToolExecutorRef) -> str:
    """Render an executor ref as a compact diagnostic label."""
    kind = ref["kind"]
    if kind == "core":
        return f"core:{ref['executor_id']}"
    if kind == "plugin":
        return f"plugin:{ref['plugin_id']}:{ref['tool_name']}"
    if kind == "channel":
        return f"channel:{ref['channel_id']}:{ref['action_id']}"
    if kind == "mcp":
        return f"mcp:{ref['server_id']}:{ref['tool_name']}"
    raise ValueError(f"Unsupported tool executor ref kind: {kind!r}")
