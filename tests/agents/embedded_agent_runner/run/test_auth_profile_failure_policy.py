"""Tests for auth profile failure policy (P2-0013)."""

from openclaw.agents.embedded_agent_runner.run.auth_profile_failure_policy import (
    resolve_auth_profile_failure_reason,
)


def test_records_shared_non_timeout_failures():
    assert (
        resolve_auth_profile_failure_reason(failover_reason="billing", policy="shared")
        == "billing"
    )
    assert (
        resolve_auth_profile_failure_reason(failover_reason="rate_limit", policy="shared")
        == "rate_limit"
    )


def test_local_policy_never_records():
    assert resolve_auth_profile_failure_reason(failover_reason="billing", policy="local") is None
    assert resolve_auth_profile_failure_reason(failover_reason="auth", policy="local") is None


def test_local_transient_rate_limit():
    assert (
        resolve_auth_profile_failure_reason(
            failover_reason="rate_limit", policy="local_transient"
        )
        == "rate_limit"
    )
    assert (
        resolve_auth_profile_failure_reason(
            failover_reason="rate_limit",
            policy="local_transient",
            transient_rate_limit=True,
        )
        is None
    )
    assert (
        resolve_auth_profile_failure_reason(failover_reason="overloaded", policy="local_transient")
        is None
    )
    assert (
        resolve_auth_profile_failure_reason(failover_reason="auth", policy="local_transient")
        == "auth"
    )


def test_timeout_only_when_provider_started():
    assert resolve_auth_profile_failure_reason(failover_reason="timeout") is None
    assert (
        resolve_auth_profile_failure_reason(failover_reason="timeout", provider_started=False)
        is None
    )
    assert (
        resolve_auth_profile_failure_reason(failover_reason="timeout", provider_started=True)
        == "timeout"
    )


def test_server_error_and_empty_response_not_persisted():
    assert resolve_auth_profile_failure_reason(failover_reason="server_error") is None
    assert resolve_auth_profile_failure_reason(failover_reason="empty_response") is None
    assert (
        resolve_auth_profile_failure_reason(failover_reason="empty_response", policy="shared")
        is None
    )


def test_format_not_persisted():
    assert resolve_auth_profile_failure_reason(failover_reason="format") is None
    assert resolve_auth_profile_failure_reason(failover_reason="format", policy="shared") is None