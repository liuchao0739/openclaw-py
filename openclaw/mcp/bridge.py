"""MCP tool bridge stub."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class McpTool:
    name: str
    description: str
    input_schema: dict[str, Any] = field(default_factory=dict)


@dataclass
class McpBridge:
    server_name: str
    tools: dict[str, McpTool] = field(default_factory=dict)

    def register_tool(self, tool: McpTool) -> None:
        self.tools[tool.name] = tool

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        if name not in self.tools:
            raise KeyError(f"unknown MCP tool: {name}")
        return {"tool": name, "arguments": arguments, "result": "ok"}
