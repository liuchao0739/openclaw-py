"""MCP (Model Context Protocol) package.

Mirrors src/mcp/. The full MCP server implementation depends on the
@modelcontextprotocol/sdk and agent tool infrastructure which are not yet
ported. This package provides type stubs and basic tool handler interfaces.
"""

from __future__ import annotations

from typing import Any, Callable, Protocol, TypedDict, runtime_checkable


class McpToolDefinition(TypedDict, total=False):
    name: str
    description: str
    inputSchema: dict[str, Any]


@runtime_checkable
class AnyAgentTool(Protocol):
    """Minimal protocol for agent tools exposed via MCP."""

    name: str
    description: str


class PluginToolsMcpHandlers:
    """MCP request handlers for plugin tools."""

    def __init__(self, tools: list[Any]) -> None:
        self._tools = tools

    async def list_tools(self) -> list[McpToolDefinition]:
        """List available tools as MCP tool definitions."""
        result: list[McpToolDefinition] = []
        for tool in self._tools:
            name = getattr(tool, "name", None) or (tool.get("name") if isinstance(tool, dict) else None)
            desc = getattr(tool, "description", None) or (tool.get("description") if isinstance(tool, dict) else None)
            if name:
                result.append(McpToolDefinition(name=name, description=desc or ""))
        return result

    async def call_tool(
        self,
        params: dict[str, Any],
        signal: Any = None,
    ) -> dict[str, Any]:
        """Call a tool by name. Stub — returns empty result."""
        return {"content": [], "isError": False}


def create_plugin_tools_mcp_handlers(tools: list[Any]) -> PluginToolsMcpHandlers:
    """Create MCP handlers for a list of agent tools."""
    return PluginToolsMcpHandlers(tools)
