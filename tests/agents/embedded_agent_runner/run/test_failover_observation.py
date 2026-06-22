"""Tests for failover observation logging (P2-0013)."""

from openclaw.agents.embedded_agent_runner.run.failover_observation import (
    create_failover_decision_logger,
    normalize_failover_decision_observation_base,
)


def test_normalize_timeout_from_timed_out():
    base = normalize_failover_decision_observation_base({"timedOut": True})
    assert base["failoverReason"] == "timeout"
    assert base["profileFailureReason"] == "timeout"


def test_failover_logger_runs_without_error(caplog):
    import logging

    caplog.set_level(logging.WARNING)
    log = create_failover_decision_logger(
        {
            "stage": "prompt",
            "runId": "run-1",
            "failoverReason": "rate_limit",
            "provider": "anthropic",
            "model": "claude",
            "fallbackConfigured": True,
        }
    )
    log("rotate_profile", {"status": 429})
    assert any("embedded run failover decision" in r.message for r in caplog.records)