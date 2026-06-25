"""Tests for cli/daemon_cli — types, token drift, status."""

from __future__ import annotations

from openclaw.cli.daemon_cli import (
    resolve_gateway_token_for_drift_check,
    run_daemon_status,
)


class TestGatewayTokenDrift:
    async def test_no_config_returns_none(self):
        result = await resolve_gateway_token_for_drift_check(None, {})
        assert result is None

    async def test_password_mode_returns_none(self):
        cfg = {"gateway": {"auth": {"mode": "password"}}}
        result = await resolve_gateway_token_for_drift_check(cfg, {})
        assert result is None

    async def test_none_mode_returns_none(self):
        cfg = {"gateway": {"auth": {"mode": "none"}}}
        result = await resolve_gateway_token_for_drift_check(cfg, {})
        assert result is None

    async def test_token_from_config(self):
        cfg = {"gateway": {"auth": {"mode": "token", "token": "secret-token"}}}
        result = await resolve_gateway_token_for_drift_check(cfg, {})
        assert result == "secret-token"

    async def test_token_from_env(self):
        cfg = {"gateway": {"auth": {"mode": "token"}}}
        result = await resolve_gateway_token_for_drift_check(cfg, {"OPENCLAW_GATEWAY_TOKEN": "env-token"})
        assert result == "env-token"

    async def test_password_fallback(self):
        cfg = {"gateway": {"auth": {"password": "pw"}}}
        env = {"OPENCLAW_GATEWAY_PASSWORD": "pw"}
        result = await resolve_gateway_token_for_drift_check(cfg, env)
        assert result is None


class TestRunDaemonStatus:
    async def test_require_rpc_without_probe(self):
        result = await run_daemon_status({"requireRpc": True, "probe": False})
        assert result["ok"] is False
        assert result["exitCode"] == 1

    async def test_basic_status(self):
        result = await run_daemon_status({"probe": False})
        assert "output" in result
        assert result["exitCode"] == 0

    async def test_json_output(self):
        result = await run_daemon_status({"probe": False, "json": True})
        assert "installed" in result["output"]  # JSON contains status fields
