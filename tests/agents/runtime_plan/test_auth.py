"""Runtime plan auth tests (P2-0014)."""

from openclaw.agents.runtime_plan.auth import build_agent_runtime_auth_plan


def test_forwards_profile_when_providers_match():
    plan = build_agent_runtime_auth_plan(
        provider="anthropic",
        auth_profile_provider="anthropic",
        session_auth_profile_id="prof-1",
    )
    assert plan["providerForAuth"] == "anthropic"
    assert plan.get("forwardedAuthProfileId") == "prof-1"


def test_no_forward_when_provider_mismatch():
    plan = build_agent_runtime_auth_plan(
        provider="anthropic",
        auth_profile_provider="openai",
        session_auth_profile_id="prof-1",
    )
    assert "forwardedAuthProfileId" not in plan


def test_codex_harness_auth():
    plan = build_agent_runtime_auth_plan(
        provider="openai",
        auth_profile_provider="openai",
        harness_id="codex",
        session_auth_profile_id="p1",
    )
    assert plan.get("harnessAuthProvider") == "openai"
    assert plan.get("forwardedAuthProfileId") == "p1"