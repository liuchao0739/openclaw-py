"""Tests for agents/runtime-plan auth."""

from openclaw.agents.runtime_plan import (
    build_agent_runtime_auth_plan,
    CODEX_HARNESS_AUTH_PROVIDER,
)


class TestBuildAgentRuntimeAuthPlan:
    def test_basic_provider_forward(self):
        result = build_agent_runtime_auth_plan(
            provider="anthropic",
            auth_profile_provider="anthropic",
            session_auth_profile_id="profile-1",
        )
        assert result["providerForAuth"] == "anthropic"
        assert result["forwardedAuthProfileId"] == "profile-1"

    def test_provider_mismatch_no_forward(self):
        result = build_agent_runtime_auth_plan(
            provider="openai",
            auth_profile_provider="anthropic",
            session_auth_profile_id="profile-1",
        )
        assert "forwardedAuthProfileId" not in result

    def test_default_auth_profile_provider(self):
        result = build_agent_runtime_auth_plan(
            provider="anthropic",
            session_auth_profile_id="profile-1",
        )
        assert result["authProfileProviderForAuth"] == "anthropic"
        assert result["forwardedAuthProfileId"] == "profile-1"

    def test_codex_harness(self):
        result = build_agent_runtime_auth_plan(
            provider="openai",
            auth_profile_provider="openai",
            session_auth_profile_id="profile-1",
            harness_id="codex",
        )
        assert result["harnessAuthProvider"] == CODEX_HARNESS_AUTH_PROVIDER
        assert result["forwardedAuthProfileId"] == "profile-1"

    def test_codex_harness_runtime(self):
        result = build_agent_runtime_auth_plan(
            provider="openai",
            harness_runtime="codex",
        )
        assert result["harnessAuthProvider"] == "openai"

    def test_harness_mismatch_no_forward(self):
        result = build_agent_runtime_auth_plan(
            provider="anthropic",
            auth_profile_provider="anthropic",
            session_auth_profile_id="profile-1",
            harness_id="codex",
        )
        assert "forwardedAuthProfileId" not in result
        assert result["harnessAuthProvider"] == "openai"

    def test_harness_forwarding_disabled(self):
        result = build_agent_runtime_auth_plan(
            provider="openai",
            auth_profile_provider="openai",
            session_auth_profile_id="profile-1",
            harness_id="codex",
            allow_harness_auth_profile_forwarding=False,
        )
        assert "forwardedAuthProfileId" not in result

    def test_candidate_ids(self):
        result = build_agent_runtime_auth_plan(
            provider="anthropic",
            auth_profile_provider="anthropic",
            session_auth_profile_id="profile-1",
            session_auth_profile_candidate_ids=["c1", "c2"],
        )
        assert result["forwardedAuthProfileCandidateIds"] == ["c1", "c2"]

    def test_no_session_profile(self):
        result = build_agent_runtime_auth_plan(
            provider="anthropic",
            auth_profile_provider="anthropic",
        )
        assert "forwardedAuthProfileId" not in result
        assert "forwardedAuthProfileCandidateIds" not in result

    def test_non_codex_harness(self):
        result = build_agent_runtime_auth_plan(
            provider="anthropic",
            harness_id="claude",
        )
        assert "harnessAuthProvider" not in result
