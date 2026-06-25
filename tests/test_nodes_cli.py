"""Tests for cli/nodes_cli — format, types, cli_utils."""

from __future__ import annotations

from openclaw.cli.nodes_cli import (
    NodesRpcOpts,
    format_permissions,
    get_nodes_theme,
    parse_node_list,
    parse_pairing_list,
    run_nodes_command,
)


class TestFormat:
    def test_format_permissions(self):
        result = format_permissions({"read": True, "write": False})
        assert result is not None
        assert "read=yes" in result
        assert "write=no" in result

    def test_format_permissions_empty(self):
        assert format_permissions({}) is None
        assert format_permissions(None) is None
        assert format_permissions("string") is None

    def test_format_permissions_sorted(self):
        result = format_permissions({"zebra": True, "apple": False})
        assert result is not None
        assert result.index("apple") < result.index("zebra")

    def test_parse_node_list_list(self):
        result = parse_node_list([{"id": "n1"}, {"id": "n2"}])
        assert len(result) == 2

    def test_parse_node_list_dict(self):
        result = parse_node_list({"nodes": [{"id": "n1"}]})
        assert len(result) == 1

    def test_parse_node_list_empty(self):
        assert parse_node_list(None) == []
        assert parse_node_list("string") == []

    def test_parse_pairing_list(self):
        result = parse_pairing_list([{"id": "p1"}])
        assert len(result) == 1


class TestCliUtils:
    def test_get_nodes_theme(self):
        theme = get_nodes_theme()
        assert "rich" in theme
        assert "heading" in theme
        assert "error" in theme

    async def test_run_nodes_command_success(self):
        async def action():
            pass

        result = await run_nodes_command("test", action)
        assert result["ok"] is True

    async def test_run_nodes_command_failure(self):
        async def action():
            raise RuntimeError("something failed")

        result = await run_nodes_command("test", action)
        assert result["ok"] is False
        assert "something failed" in result["error"]

    async def test_run_nodes_command_unauthorized(self):
        async def action():
            raise RuntimeError("Unauthorized: 401")

        result = await run_nodes_command("test", action)
        assert result["ok"] is False
        assert "Hint" in result["error"]


class TestTypes:
    def test_opts_creation(self):
        opts: NodesRpcOpts = {"url": "ws://localhost:8080", "token": "secret"}
        assert opts["url"] == "ws://localhost:8080"
