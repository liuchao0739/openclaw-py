"""Tests for node-host with_timeout module."""

import asyncio
import pytest

from openclaw.node_host.with_timeout import with_timeout


async def _quick_work(signal):
    return 42


async def _slow_work(signal):
    await asyncio.sleep(10)
    return 99


async def _check_signal_work(signal):
    if signal is not None:
        await asyncio.sleep(0.01)
        return "ok"
    return "no signal"


class TestWithTimeout:
    def test_no_timeout(self):
        result = asyncio.run(with_timeout(_quick_work))
        assert result == 42

    def test_completes_before_timeout(self):
        result = asyncio.run(with_timeout(_quick_work, 5000))
        assert result == 42

    def test_times_out(self):
        with pytest.raises(asyncio.TimeoutError):
            asyncio.run(with_timeout(_slow_work, 50, "test op"))

    def test_label_in_error(self):
        with pytest.raises(asyncio.TimeoutError, match="custom label"):
            asyncio.run(with_timeout(_slow_work, 50, "custom label"))

    def test_signal_passed_to_work(self):
        result = asyncio.run(with_timeout(_check_signal_work, 5000))
        assert result == "ok"

    def test_zero_timeout_returns_none(self):
        # 0 ms timeout resolves to None → no timeout applied
        result = asyncio.run(with_timeout(_quick_work, 0))
        assert result == 42

    def test_negative_timeout_returns_none(self):
        result = asyncio.run(with_timeout(_quick_work, -100))
        assert result == 42

    def test_none_timeout(self):
        result = asyncio.run(with_timeout(_quick_work, None))
        assert result == 42
