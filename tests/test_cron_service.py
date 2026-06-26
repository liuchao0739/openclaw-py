"""Tests for cron/service core modules."""

import asyncio
from types import SimpleNamespace

import pytest

from openclaw.cron.service.task_ledger import CRON_TASK_RUNNING_PROGRESS_SUMMARY
from openclaw.cron.service.initial_delivery import resolve_initial_cron_delivery
from openclaw.cron.service.timeout_policy import (
    DEFAULT_JOB_TIMEOUT_MS,
    AGENT_TURN_SAFETY_TIMEOUT_MS,
    resolve_cron_job_timeout_ms,
)
from openclaw.cron.service.locked import locked, _reset_store_locks_for_tests


def test_task_running_progress_summary():
    assert CRON_TASK_RUNNING_PROGRESS_SUMMARY == "Running cron job."


class TestInitialDelivery:
    def test_explicit_delivery_returned(self):
        result = resolve_initial_cron_delivery({"delivery": {"mode": "silent"}})
        assert result == {"mode": "silent"}

    def test_isolated_agent_turn_gets_announce(self):
        result = resolve_initial_cron_delivery(
            {"sessionTarget": "isolated", "payload": {"kind": "agentTurn"}}
        )
        assert result == {"mode": "announce"}

    def test_isolated_command_gets_announce(self):
        result = resolve_initial_cron_delivery(
            {"sessionTarget": "isolated", "payload": {"kind": "command"}}
        )
        assert result == {"mode": "announce"}

    def test_non_isolated_no_default(self):
        result = resolve_initial_cron_delivery(
            {"sessionTarget": "main", "payload": {"kind": "agentTurn"}}
        )
        assert result is None

    def test_isolated_other_payload_no_default(self):
        result = resolve_initial_cron_delivery(
            {"sessionTarget": "isolated", "payload": {"kind": "other"}}
        )
        assert result is None


class TestTimeoutPolicy:
    def test_agent_turn_default(self):
        job = {"payload": {"kind": "agentTurn"}}
        assert resolve_cron_job_timeout_ms(job) == AGENT_TURN_SAFETY_TIMEOUT_MS

    def test_command_default(self):
        job = {"payload": {"kind": "command"}}
        assert resolve_cron_job_timeout_ms(job) == DEFAULT_JOB_TIMEOUT_MS

    def test_other_payload_default(self):
        job = {"payload": {"kind": "other"}}
        assert resolve_cron_job_timeout_ms(job) == DEFAULT_JOB_TIMEOUT_MS

    def test_explicit_timeout(self):
        job = {"payload": {"kind": "agentTurn", "timeoutSeconds": 30}}
        assert resolve_cron_job_timeout_ms(job) == 30000

    def test_explicit_timeout_command(self):
        job = {"payload": {"kind": "command", "timeoutSeconds": 60}}
        assert resolve_cron_job_timeout_ms(job) == 60000

    def test_zero_timeout_disables(self):
        job = {"payload": {"kind": "agentTurn", "timeoutSeconds": 0}}
        assert resolve_cron_job_timeout_ms(job) is None

    def test_negative_timeout_disables(self):
        job = {"payload": {"kind": "agentTurn", "timeoutSeconds": -5}}
        assert resolve_cron_job_timeout_ms(job) is None

    def test_constants(self):
        assert DEFAULT_JOB_TIMEOUT_MS == 600_000
        assert AGENT_TURN_SAFETY_TIMEOUT_MS == 3_600_000


class TestLocked:
    @pytest.fixture(autouse=True)
    def _clean(self):
        _reset_store_locks_for_tests()
        yield
        _reset_store_locks_for_tests()

    def test_serializes_same_store(self):
        store_locks: dict = {}
        order = []

        class Deps:
            store_path = "/store/a"

        state = SimpleNamespace(deps=Deps(), op=None)

        async def task_a():
            order.append("a-start")
            await asyncio.sleep(0.01)
            order.append("a-end")

        async def task_b():
            order.append("b-start")
            await asyncio.sleep(0.01)
            order.append("b-end")

        async def main():
            t1 = asyncio.create_task(locked(state, task_a, _store_locks=store_locks))
            t2 = asyncio.create_task(locked(state, task_b, _store_locks=store_locks))
            await asyncio.gather(t1, t2)

        asyncio.run(main())
        assert order == ["a-start", "a-end", "b-start", "b-end"]

    def test_returns_fn_result(self):
        store_locks: dict = {}

        class Deps:
            store_path = "/store/x"

        state = SimpleNamespace(deps=Deps(), op=None)

        async def returns_value():
            return 42

        result = asyncio.run(locked(state, returns_value, _store_locks=store_locks))
        assert result == 42

    def test_different_stores_parallel(self):
        store_locks: dict = {}

        class DepsA:
            store_path = "/store/a"

        class DepsB:
            store_path = "/store/b"

        state_a = SimpleNamespace(deps=DepsA(), op=None)
        state_b = SimpleNamespace(deps=DepsB(), op=None)
        order = []

        async def task(name, delay):
            order.append(f"{name}-start")
            await asyncio.sleep(delay)
            order.append(f"{name}-end")

        async def main():
            t1 = asyncio.create_task(locked(state_a, lambda: task("a", 0.02), _store_locks=store_locks))
            t2 = asyncio.create_task(locked(state_b, lambda: task("b", 0.01), _store_locks=store_locks))
            await asyncio.gather(t1, t2)

        asyncio.run(main())
        # b should finish before a since they use different stores
        assert order.index("b-end") < order.index("a-end")
