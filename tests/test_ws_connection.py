"""Tests for gateway/server/ws-connection modules."""

import pytest

from openclaw.gateway.server.ws_connection.unauthorized_flood_guard import (
    UnauthorizedFloodGuard,
    is_unauthorized_role_error,
)
from openclaw.gateway.server.ws_connection.auth_messages import (
    format_gateway_auth_failure_message,
)


class TestUnauthorizedFloodGuard:
    def test_first_failure_logs(self):
        guard = UnauthorizedFloodGuard()
        d = guard.register_unauthorized()
        assert d.should_log is True
        assert d.should_close is False
        assert d.count == 1

    def test_second_failure_suppressed(self):
        guard = UnauthorizedFloodGuard()
        guard.register_unauthorized()
        d = guard.register_unauthorized()
        assert d.should_log is False
        assert d.count == 2

    def test_close_after_threshold(self):
        guard = UnauthorizedFloodGuard({"closeAfter": 3})
        for i in range(1, 4):
            d = guard.register_unauthorized()
            assert d.should_close is False
        d = guard.register_unauthorized()
        assert d.should_close is True
        assert d.count == 4

    def test_log_every(self):
        guard = UnauthorizedFloodGuard({"closeAfter": 1000, "logEvery": 5})
        results = []
        for _ in range(15):
            results.append(guard.register_unauthorized())
        logged = [r for r in results if r.should_log]
        # logs at 1, 5, 10, 15
        assert len(logged) == 4

    def test_suppressed_count_reset_on_log(self):
        guard = UnauthorizedFloodGuard({"closeAfter": 1000, "logEvery": 3})
        guard.register_unauthorized()  # logs (count=1)
        d2 = guard.register_unauthorized()  # suppressed
        assert d2.should_log is False
        d3 = guard.register_unauthorized()  # logs (count=3)
        assert d3.should_log is True
        assert d3.suppressed_since_last_log == 1

    def test_reset(self):
        guard = UnauthorizedFloodGuard({"closeAfter": 2})
        guard.register_unauthorized()
        guard.register_unauthorized()
        guard.reset()
        d = guard.register_unauthorized()
        assert d.count == 1

    def test_close_logs(self):
        guard = UnauthorizedFloodGuard({"closeAfter": 1, "logEvery": 100})
        guard.register_unauthorized()  # count=1, logs
        d = guard.register_unauthorized()  # count=2 > 1, should_close=True, should_log=True
        assert d.should_close is True
        assert d.should_log is True


class TestIsUnauthorizedRoleError:
    def test_valid(self):
        err = {"code": "invalid_request", "message": "unauthorized role: guest"}
        assert is_unauthorized_role_error(err) is True

    def test_wrong_code(self):
        err = {"code": "other", "message": "unauthorized role: guest"}
        assert is_unauthorized_role_error(err) is False

    def test_wrong_message_prefix(self):
        err = {"code": "invalid_request", "message": "forbidden"}
        assert is_unauthorized_role_error(err) is False

    def test_none(self):
        assert is_unauthorized_role_error(None) is False

    def test_non_string_message(self):
        err = {"code": "invalid_request", "message": 42}
        assert is_unauthorized_role_error(err) is False


class TestAuthMessages:
    def test_token_missing_cli(self):
        msg = format_gateway_auth_failure_message({
            "authMode": "token",
            "authProvided": "none",
            "reason": "token_missing",
            "client": {"mode": "cli"},
        })
        assert "gateway.remote.token" in msg

    def test_token_missing_ui(self):
        msg = format_gateway_auth_failure_message({
            "authMode": "token",
            "authProvided": "none",
            "reason": "token_missing",
            "client": {"mode": "operator-ui"},
        })
        assert "dashboard URL" in msg

    def test_token_missing_webchat(self):
        msg = format_gateway_auth_failure_message({
            "authMode": "token",
            "authProvided": "none",
            "reason": "token_missing",
            "client": {"mode": "webchat"},
        })
        assert "dashboard URL" in msg

    def test_token_missing_default(self):
        msg = format_gateway_auth_failure_message({
            "authMode": "token",
            "authProvided": "none",
            "reason": "token_missing",
        })
        assert "provide gateway auth token" in msg

    def test_password_mismatch_cli(self):
        msg = format_gateway_auth_failure_message({
            "authMode": "password",
            "authProvided": "password",
            "reason": "password_mismatch",
            "client": {"mode": "cli"},
        })
        assert "gateway.remote.password" in msg

    def test_bootstrap_token_invalid(self):
        msg = format_gateway_auth_failure_message({
            "authMode": "token",
            "authProvided": "bootstrap-token",
            "reason": "bootstrap_token_invalid",
        })
        assert "bootstrap token" in msg

    def test_rate_limited(self):
        msg = format_gateway_auth_failure_message({
            "authMode": "token",
            "authProvided": "none",
            "reason": "rate_limited",
        })
        assert "too many" in msg

    def test_default_unauthorized(self):
        msg = format_gateway_auth_failure_message({
            "authMode": "none",
            "authProvided": "none",
        })
        assert msg == "unauthorized"

    def test_token_mode_none_provided_no_reason(self):
        msg = format_gateway_auth_failure_message({
            "authMode": "token",
            "authProvided": "none",
        })
        assert "token missing" in msg

    def test_device_token_rejected(self):
        msg = format_gateway_auth_failure_message({
            "authMode": "token",
            "authProvided": "device-token",
        })
        assert "device token rejected" in msg
