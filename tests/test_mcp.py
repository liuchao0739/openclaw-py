"""Tests for MCP package."""

import asyncio

from openclaw.mcp import (
    PluginToolsMcpHandlers,
    create_plugin_tools_mcp_handlers,
)


class TestPluginToolsMcpHandlers:
    def test_list_tools_empty(self):
        handlers = PluginToolsMcpHandlers([])
        result = asyncio.run(handlers.list_tools())
        assert result == []

    def test_list_tools_with_objects(self):
        class Tool:
            def __init__(self, name, desc):
                self.name = name
                self.description = desc
        handlers = PluginToolsMcpHandlers([Tool("cron", "Cron tool"), Tool("search", "Search")])
        result = asyncio.run(handlers.list_tools())
        assert len(result) == 2
        assert result[0]["name"] == "cron"
        assert result[0]["description"] == "Cron tool"

    def test_list_tools_with_dicts(self):
        handlers = PluginToolsMcpHandlers([
            {"name": "tool1", "description": "desc1"},
        ])
        result = asyncio.run(handlers.list_tools())
        assert len(result) == 1
        assert result[0]["name"] == "tool1"

    def test_list_tools_skips_no_name(self):
        class NoName:
            description = "no name"
        handlers = PluginToolsMcpHandlers([NoName()])
        result = asyncio.run(handlers.list_tools())
        assert result == []

    def test_call_tool_stub(self):
        handlers = PluginToolsMcpHandlers([])
        result = asyncio.run(handlers.call_tool({"name": "test"}))
        assert result["isError"] is False
        assert result["content"] == []

    def test_create_handlers(self):
        handlers = create_plugin_tools_mcp_handlers([])
        assert isinstance(handlers, PluginToolsMcpHandlers)
