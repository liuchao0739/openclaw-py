"""Tests for infra/outbound core modules."""

import asyncio
import pytest

from openclaw.infra.outbound.identity_types import OutboundIdentity
from openclaw.infra.outbound.thread_id import normalize_outbound_thread_id
from openclaw.infra.outbound.abort import throw_if_aborted


class TestOutboundIdentity:
    def test_typeddict(self):
        identity: OutboundIdentity = {"name": "Agent", "emoji": "🤖"}
        assert identity["name"] == "Agent"


class TestNormalizeOutboundThreadId:
    def test_string(self):
        assert normalize_outbound_thread_id("thread-123") == "thread-123"

    def test_integer(self):
        assert normalize_outbound_thread_id(123) == "123"

    def test_float(self):
        assert normalize_outbound_thread_id(456.0) == "456"

    def test_none(self):
        assert normalize_outbound_thread_id(None) is None

    def test_empty_string(self):
        assert normalize_outbound_thread_id("") is None
        assert normalize_outbound_thread_id("  ") is None

    def test_bool_rejected(self):
        assert normalize_outbound_thread_id(True) is None

    def test_nan_rejected(self):
        assert normalize_outbound_thread_id(float("nan")) is None

    def test_trims_string(self):
        assert normalize_outbound_thread_id("  thread-1  ") == "thread-1"


class TestThrowIfAborted:
    def test_no_signal(self):
        throw_if_aborted(None)  # should not raise

    def test_not_aborted(self):
        class Signal:
            aborted = False
        throw_if_aborted(Signal())  # should not raise

    def test_aborted_raises(self):
        class Signal:
            aborted = True
        with pytest.raises(asyncio.CancelledError):
            throw_if_aborted(Signal())
