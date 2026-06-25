"""Tests for cli/gateway_cli — runtime hooks, shared, call."""

from __future__ import annotations

from openclaw.cli.gateway_cli import (
    DEFAULT_GATEWAY_RPC_TIMEOUT_MS,
    call_gateway_cli,
    get_gateway_run_runtime_hooks,
    install_gateway_run_runtime_hooks,
    parse_timeout_ms_with_fallback,
    render_gateway_service_stop_hints,
)


class TestRuntimeHooks:
    def test_get_empty(self):
        hooks = get_gateway_run_runtime_hooks()
        assert hooks == {}

    def test_install_and_restore(self):
        test_hooks = {"releaseManagedProxy": lambda: None}
        restore = install_gateway_run_runtime_hooks(test_hooks)
        assert get_gateway_run_runtime_hooks() is test_hooks
        restore()
        assert get_gateway_run_runtime_hooks() == {}

    def test_install_overwrite(self):
        hooks1 = {"a": 1}
        hooks2 = {"b": 2}
        r1 = install_gateway_run_runtime_hooks(hooks1)
        r2 = install_gateway_run_runtime_hooks(hooks2)
        assert get_gateway_run_runtime_hooks() is hooks2
        r2()
        assert get_gateway_run_runtime_hooks() is hooks1
        r1()
        assert get_gateway_run_runtime_hooks() == {}


class TestShared:
    def test_render_stop_hints(self):
        hints = render_gateway_service_stop_hints()
        assert len(hints) >= 1
        assert "openclaw gateway stop" in hints[0]

    def test_render_with_profile(self):
        hints = render_gateway_service_stop_hints({"OPENCLAW_PROFILE": "test"})
        assert len(hints) >= 1


class TestCall:
    def test_parse_timeout_default(self):
        assert parse_timeout_ms_with_fallback(None) == DEFAULT_GATEWAY_RPC_TIMEOUT_MS
        assert parse_timeout_ms_with_fallback("") == DEFAULT_GATEWAY_RPC_TIMEOUT_MS

    def test_parse_timeout_valid(self):
        assert parse_timeout_ms_with_fallback("5000") == 5000

    def test_parse_timeout_invalid(self):
        assert parse_timeout_ms_with_fallback("abc") == DEFAULT_GATEWAY_RPC_TIMEOUT_MS
        assert parse_timeout_ms_with_fallback("0") == DEFAULT_GATEWAY_RPC_TIMEOUT_MS
        assert parse_timeout_ms_with_fallback("-5") == DEFAULT_GATEWAY_RPC_TIMEOUT_MS

    async def test_call_gateway_unavailable(self):
        result = await call_gateway_cli("test.method", {})
        assert result.get("ok") is False
        assert "error" in result
