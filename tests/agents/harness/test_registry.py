"""Harness registry tests (P2-0011)."""

import pytest

from openclaw.agents.harness.errors import MissingAgentHarnessError, is_missing_agent_harness_error
from openclaw.agents.harness.registry import (
    get_agent_harness,
    register_agent_harness,
    reset_agent_harness_registry_for_tests,
)


class _Harness:
    id = "test-harness"
    label = "Test"

    def supports(self, ctx):
        return {"supported": True}

    async def runAttempt(self, params):
        return {}


@pytest.fixture(autouse=True)
def _clear_registry():
    reset_agent_harness_registry_for_tests()
    yield
    reset_agent_harness_registry_for_tests()


def test_register_and_get():
    register_agent_harness(_Harness(), owner_plugin_id="plugin-a")
    assert get_agent_harness("test-harness") is not None


def test_missing_harness_error():
    err = MissingAgentHarnessError("missing")
    assert is_missing_agent_harness_error(err)
    assert err.harness_id == "missing"