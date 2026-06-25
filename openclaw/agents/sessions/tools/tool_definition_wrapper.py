"""Tool definition/AgentTool adapters.

Bridges extension-style ToolDefinition objects and core runtime AgentTool objects.
"""

from __future__ import annotations

from typing import Any


def wrap_tool_definition(
    definition: dict[str, Any],
    ctx_factory: Any = None,
) -> dict[str, Any]:
    """Wrap a ToolDefinition into an AgentTool for the core runtime."""
    async def _execute(tool_call_id: str, params: Any, signal: Any, on_update: Any) -> Any:
        ctx = ctx_factory() if ctx_factory else None
        return await definition["execute"](tool_call_id, params, signal, on_update, ctx)

    tool: dict[str, Any] = {
        "name": definition["name"],
        "label": definition.get("label", definition["name"]),
        "description": definition.get("description", ""),
        "parameters": definition.get("parameters"),
        "execute": _execute,
    }
    if "prepareArguments" in definition:
        tool["prepareArguments"] = definition["prepareArguments"]
    if "executionMode" in definition:
        tool["executionMode"] = definition["executionMode"]
    return tool


def wrap_tool_definitions(
    definitions: list[dict[str, Any]],
    ctx_factory: Any = None,
) -> list[dict[str, Any]]:
    """Wrap multiple ToolDefinitions into AgentTools."""
    return [wrap_tool_definition(d, ctx_factory) for d in definitions]


def create_tool_definition_from_agent_tool(tool: dict[str, Any]) -> dict[str, Any]:
    """Synthesize a minimal ToolDefinition from an AgentTool."""
    async def _execute(tool_call_id: str, params: Any, signal: Any, on_update: Any) -> Any:
        return await tool["execute"](tool_call_id, params, signal, on_update)

    definition: dict[str, Any] = {
        "name": tool["name"],
        "label": tool.get("label", tool["name"]),
        "description": tool.get("description", ""),
        "parameters": tool.get("parameters"),
        "execute": _execute,
    }
    if "prepareArguments" in tool:
        definition["prepareArguments"] = tool["prepareArguments"]
    if "executionMode" in tool:
        definition["executionMode"] = tool["executionMode"]
    return definition
