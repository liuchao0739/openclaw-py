"""Tests for cron/isolated-agent core modules."""

import asyncio

import pytest

from openclaw.cron.isolated_agent.run_timeout import (
    resolve_cron_run_timeout_override_ms,
)
from openclaw.cron.isolated_agent.job_fixtures import (
    make_isolated_agent_job_fixture,
    make_isolated_agent_params_fixture,
)
from openclaw.cron.isolated_agent.channel_output_policy import (
    resolve_cron_channel_output_policy,
    resolve_current_channel_target,
)
from openclaw.cron.isolated_agent.delivery_logger_runtime import (
    log_error,
    log_warn,
)


class TestRunTimeout:
    def test_integer_seconds(self):
        assert resolve_cron_run_timeout_override_ms(30) == 30000

    def test_float_seconds(self):
        assert resolve_cron_run_timeout_override_ms(1.5) == 1500

    def test_none(self):
        assert resolve_cron_run_timeout_override_ms(None) is None

    def test_bool_rejected(self):
        assert resolve_cron_run_timeout_override_ms(True) is None
        assert resolve_cron_run_timeout_override_ms(False) is None

    def test_string_rejected(self):
        assert resolve_cron_run_timeout_override_ms("30") is None

    def test_zero(self):
        assert resolve_cron_run_timeout_override_ms(0) == 0

    def test_negative_clamped(self):
        assert resolve_cron_run_timeout_override_ms(-5) == 0

    def test_nan(self):
        assert resolve_cron_run_timeout_override_ms(float("nan")) is None

    def test_inf(self):
        assert resolve_cron_run_timeout_override_ms(float("inf")) is None
        assert resolve_cron_run_timeout_override_ms(float("-inf")) is None

    def test_very_large_clamped(self):
        # 2^31 seconds → clamped to 2^31 - 1 ms
        result = resolve_cron_run_timeout_override_ms(2**31)
        assert result == 2**31 - 1


class TestJobFixtures:
    def test_default_job(self):
        job = make_isolated_agent_job_fixture()
        assert job["id"] == "test-job"
        assert job["name"] == "Test Job"
        assert job["schedule"]["expr"] == "0 9 * * *"
        assert job["sessionTarget"] == "isolated"
        assert job["payload"]["kind"] == "agentTurn"

    def test_job_overrides(self):
        job = make_isolated_agent_job_fixture({"id": "custom", "name": "Custom"})
        assert job["id"] == "custom"
        assert job["name"] == "Custom"
        assert job["schedule"]["expr"] == "0 9 * * *"

    def test_job_deep_copy(self):
        job = make_isolated_agent_job_fixture()
        job["payload"]["message"] = "changed"
        job2 = make_isolated_agent_job_fixture()
        assert job2["payload"]["message"] == "test"

    def test_default_params(self):
        params = make_isolated_agent_params_fixture()
        assert params["cfg"] == {}
        assert params["message"] == "test"
        assert params["sessionKey"] == "cron:test"
        assert params["job"]["id"] == "test-job"

    def test_params_with_job_override(self):
        params = make_isolated_agent_params_fixture({"job": {"id": "x"}})
        assert params["job"]["id"] == "x"
        assert params["job"]["name"] == "Test Job"

    def test_params_with_other_overrides(self):
        params = make_isolated_agent_params_fixture({"message": "hello"})
        assert params["message"] == "hello"


class TestChannelOutputPolicy:
    def test_no_channel_no_delivery(self):
        result = asyncio.run(resolve_cron_channel_output_policy(None))
        assert result["prefer_final_assistant_visible_text"] is True

    def test_no_channel_with_delivery(self):
        result = asyncio.run(
            resolve_cron_channel_output_policy(None, {"deliveryRequested": True})
        )
        assert result["prefer_final_assistant_visible_text"] is False

    def test_empty_channel(self):
        result = asyncio.run(resolve_cron_channel_output_policy(""))
        assert result["prefer_final_assistant_visible_text"] is True

    def test_channel_no_runtime(self):
        result = asyncio.run(resolve_cron_channel_output_policy("discord"))
        assert result["prefer_final_assistant_visible_text"] is False

    def test_resolve_current_target_no_to(self):
        assert asyncio.run(resolve_current_channel_target({"to": ""})) is None
        assert asyncio.run(resolve_current_channel_target({})) is None

    def test_resolve_current_target_no_channel(self):
        assert asyncio.run(resolve_current_channel_target({"to": "123"})) == "123"


class TestDeliveryLogger:
    def test_log_error_writes_stderr(self, capsys):
        log_error("oops")
        captured = capsys.readouterr()
        assert "oops" in captured.err

    def test_log_warn_writes_stderr(self, capsys):
        log_warn("careful")
        captured = capsys.readouterr()
        assert "careful" in captured.err

    def test_log_with_args(self, capsys):
        log_error("err", 42, "detail")
        captured = capsys.readouterr()
        assert "err" in captured.err
        assert "42" in captured.err
        assert "detail" in captured.err
