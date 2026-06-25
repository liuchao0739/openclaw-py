"""Tests for cli/node_cli — daemon lifecycle and registration."""

from __future__ import annotations

from openclaw.cli.node_cli import (
    DEFAULT_NODE_DAEMON_RUNTIME,
    is_node_daemon_runtime,
    run_node_daemon_install,
    run_node_daemon_restart,
    run_node_daemon_start,
    run_node_daemon_status,
    run_node_daemon_stop,
    run_node_daemon_uninstall,
)


class TestDaemonRuntime:
    def test_default_runtime(self):
        assert DEFAULT_NODE_DAEMON_RUNTIME == "auto"

    def test_is_valid_runtime(self):
        assert is_node_daemon_runtime("auto") is True
        assert is_node_daemon_runtime("native") is True
        assert is_node_daemon_runtime("docker") is True

    def test_is_invalid_runtime(self):
        assert is_node_daemon_runtime("invalid") is False
        assert is_node_daemon_runtime(None) is False
        assert is_node_daemon_runtime("") is False


class TestDaemonStatus:
    async def test_basic_status(self):
        result = await run_node_daemon_status({})
        assert result["ok"] is True
        assert "output" in result

    async def test_json_status(self):
        result = await run_node_daemon_status({"json": True})
        assert "installed" in result["output"]


class TestDaemonLifecycle:
    async def test_install(self):
        result = await run_node_daemon_install({})
        assert result["ok"] is True

    async def test_start(self):
        result = await run_node_daemon_start({})
        assert result["ok"] is True

    async def test_stop(self):
        result = await run_node_daemon_stop({})
        assert result["ok"] is True

    async def test_restart(self):
        result = await run_node_daemon_restart({})
        assert result["ok"] is True

    async def test_uninstall(self):
        result = await run_node_daemon_uninstall({})
        assert result["ok"] is True
