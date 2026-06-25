"""Tool wrappers for extension-registered tools.

These wrappers adapt tool execution so extension tools receive the runner context.
"""

from __future__ import annotations

from typing import Any


def wrap_registered_tool(
    registered_tool: dict[str, Any],
    runner: Any,
) -> dict[str, Any]:
    """Wrap a RegisteredTool into an agent tool dict.

    Uses the runner's create_context() for consistent context across tools.
    """
    definition = registered_tool["definition"]

    async def _execute(
        tool_call_id: str,
        params: Any,
        signal: Any,
        on_update: Any,
    ) -> Any:
        ctx = runner.create_context()
        return await definition["execute"](tool_call_id, params, signal, on_update, ctx)

    return {
        "name": definition["name"],
        "label": definition.get("label", definition["name"]),
        "description": definition.get("description", ""),
        "parameters": definition.get("parameters"),
        "execute": _execute,
        **({"renderShell": definition["renderShell"]} if "renderShell" in definition else {}),
        **({"executionMode": definition["executionMode"]} if "executionMode" in definition else {}),
    }


def wrap_registered_tools(
    registered_tools: list[dict[str, Any]],
    runner: Any,
) -> list[dict[str, Any]]:
    """Wrap all registered tools into agent tool dicts."""
    return [wrap_registered_tool(rt, runner) for rt in registered_tools]
