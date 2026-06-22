"""Tests aligned with failover-policy.test.ts."""

from openclaw.agents.embedded_agent_runner.run.failover_policy import (
    merge_retry_failover_reason,
    resolve_run_failover_decision,
)


def test_retry_limit_escalates_rate_limit():
    assert resolve_run_failover_decision(
        {
            "stage": "retry_limit",
            "fallbackConfigured": True,
            "failoverReason": "rate_limit",
        }
    ) == {"action": "fallback_model", "reason": "rate_limit"}


def test_retry_limit_timeout_returns_payload():
    assert resolve_run_failover_decision(
        {
            "stage": "retry_limit",
            "fallbackConfigured": True,
            "failoverReason": "timeout",
        }
    ) == {"action": "return_error_payload"}


def test_prompt_rotate_before_fallback():
    assert resolve_run_failover_decision(
        {
            "stage": "prompt",
            "aborted": False,
            "externalAbort": False,
            "fallbackConfigured": True,
            "failoverFailure": True,
            "failoverReason": "rate_limit",
            "profileRotated": False,
        }
    ) == {"action": "rotate_profile", "reason": "rate_limit"}


def test_prompt_fallback_after_rotation():
    assert resolve_run_failover_decision(
        {
            "stage": "prompt",
            "aborted": False,
            "externalAbort": False,
            "fallbackConfigured": True,
            "failoverFailure": True,
            "failoverReason": "rate_limit",
            "profileRotated": True,
        }
    ) == {"action": "fallback_model", "reason": "rate_limit"}


def test_prompt_format_terminal():
    assert resolve_run_failover_decision(
        {
            "stage": "prompt",
            "aborted": False,
            "externalAbort": False,
            "fallbackConfigured": True,
            "failoverFailure": True,
            "failoverReason": "format",
            "profileRotated": False,
        }
    ) == {"action": "surface_error", "reason": "format"}


def test_merge_retry_failover_reason():
    assert merge_retry_failover_reason(previous="auth", failover_reason=None, timed_out=True) == "timeout"
    assert merge_retry_failover_reason(previous="auth", failover_reason="rate_limit") == "rate_limit"