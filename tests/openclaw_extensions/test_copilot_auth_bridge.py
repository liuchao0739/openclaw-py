"""Tests for copilot auth bridge plugin behavior."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from openclaw_extensions.copilot.src.auth_bridge import (
    COPILOT_DEFAULT_AGENT_ID,
    COPILOT_TOKEN_PROFILE_ERROR,
    resolve_copilot_auth,
    sanitize_agent_id,
    token_fingerprint,
)


def clean_env() -> dict[str, str]:
    return {}


FAKE_HOME = "/fake-home"


def fake_home_dir() -> str:
    return FAKE_HOME


class TestSanitizeAgentId:
    def test_returns_default_for_null_undefined_empty(self) -> None:
        assert sanitize_agent_id(None) == COPILOT_DEFAULT_AGENT_ID
        assert sanitize_agent_id("") == COPILOT_DEFAULT_AGENT_ID
        assert sanitize_agent_id("   ") == COPILOT_DEFAULT_AGENT_ID

    def test_lowercases_and_accepts_alnum_dash_underscore(self) -> None:
        assert sanitize_agent_id("Agent-1") == "agent-1"
        assert sanitize_agent_id("my_agent_42") == "my_agent_42"
        assert sanitize_agent_id("a") == "a"

    def test_rejects_path_traversal_segments_and_falls_back_to_default(self) -> None:
        assert sanitize_agent_id("../etc/passwd") == COPILOT_DEFAULT_AGENT_ID
        assert sanitize_agent_id("../..") == COPILOT_DEFAULT_AGENT_ID
        assert sanitize_agent_id("a/b") == COPILOT_DEFAULT_AGENT_ID
        assert sanitize_agent_id("a\\b") == COPILOT_DEFAULT_AGENT_ID
        assert sanitize_agent_id("a\u0000b") == COPILOT_DEFAULT_AGENT_ID

    def test_rejects_ids_that_do_not_start_with_alnum(self) -> None:
        assert sanitize_agent_id("-foo") == COPILOT_DEFAULT_AGENT_ID
        assert sanitize_agent_id("_bar") == COPILOT_DEFAULT_AGENT_ID

    def test_rejects_ids_longer_than_64_chars(self) -> None:
        assert sanitize_agent_id("a" * 64) == "a" * 64
        assert sanitize_agent_id("a" * 65) == COPILOT_DEFAULT_AGENT_ID


class TestTokenFingerprint:
    def test_returns_a_stable_sha256_prefixed_12_hex_fingerprint(self) -> None:
        a = token_fingerprint("hello")
        b = token_fingerprint("hello")
        assert a == b
        assert a.startswith("sha256:")
        assert len(a) == len("sha256:") + 12
        expected = "sha256:" + hashlib.sha256(b"hello").hexdigest()[:12]
        assert a == expected

    def test_differs_across_distinct_inputs(self) -> None:
        assert token_fingerprint("alpha") != token_fingerprint("beta")
        assert token_fingerprint("token-v1") != token_fingerprint("token-v2")

    def test_never_contains_the_raw_token(self) -> None:
        token = "ghp_abcdefghijklmnop"
        assert token not in token_fingerprint(token)


class TestResolveCopilotAuthCopilotHome:
    def test_uses_explicit_copilot_home_when_provided(self) -> None:
        result = resolve_copilot_auth(
            agent_id="agent-1",
            copilot_home="/explicit/home",
            env=clean_env(),
            home_dir=fake_home_dir,
        )
        assert result["copilot_home"] == str(Path("/explicit/home").resolve())

    def test_falls_back_to_agent_dir_copilot_when_copilot_home_is_absent(self) -> None:
        result = resolve_copilot_auth(
            agent_id="agent-1",
            agent_dir="/agent/dir",
            env=clean_env(),
            home_dir=fake_home_dir,
        )
        assert result["copilot_home"] == str(Path("/agent/dir").joinpath("copilot").resolve())

    def test_synthesises_per_agent_default_from_home_dir_when_no_path_is_given(self) -> None:
        result = resolve_copilot_auth(
            agent_id="agent-1",
            env=clean_env(),
            home_dir=fake_home_dir,
        )
        assert result["copilot_home"] == str(
            Path(FAKE_HOME).joinpath(".openclaw", "agents", "agent-1", "copilot").resolve()
        )

    def test_respects_openclaw_home_env_var_as_the_home_root(self) -> None:
        result = resolve_copilot_auth(
            agent_id="agent-1",
            env={"OPENCLAW_HOME": "/custom/openclaw"},
            home_dir=fake_home_dir,
        )
        assert result["copilot_home"] == str(
            Path("/custom/openclaw").joinpath(".openclaw", "agents", "agent-1", "copilot").resolve()
        )

    def test_uses_the_default_agent_id_when_agent_id_is_invalid_or_missing(self) -> None:
        result = resolve_copilot_auth(
            agent_id=None,
            env=clean_env(),
            home_dir=fake_home_dir,
        )
        assert result["agent_id"] == COPILOT_DEFAULT_AGENT_ID
        assert result["copilot_home"] == str(
            Path(FAKE_HOME)
            .joinpath(".openclaw", "agents", COPILOT_DEFAULT_AGENT_ID, "copilot")
            .resolve()
        )

    def test_isolates_per_agent_copilot_home_between_agents(self) -> None:
        a = resolve_copilot_auth(
            agent_id="agent-a",
            env=clean_env(),
            home_dir=fake_home_dir,
        )
        b = resolve_copilot_auth(
            agent_id="agent-b",
            env=clean_env(),
            home_dir=fake_home_dir,
        )
        assert a["copilot_home"] != b["copilot_home"]
        assert a["copilot_home"].endswith(str(Path("agent-a") / "copilot"))
        assert b["copilot_home"].endswith(str(Path("agent-b") / "copilot"))


class TestResolveCopilotAuthAuthMode:
    def test_returns_use_logged_in_user_when_auth_use_logged_in_user_true(self) -> None:
        result = resolve_copilot_auth(
            agent_id="agent-1",
            auth={"use_logged_in_user": True, "git_hub_token": "should-be-ignored"},
            env={"GITHUB_TOKEN": "env-token"},
            home_dir=fake_home_dir,
        )
        assert result["auth_mode"] == "useLoggedInUser"
        assert "git_hub_token" not in result
        assert "auth_profile_id" not in result
        assert "auth_profile_version" not in result

    def test_returns_git_hub_token_when_explicit_token_and_profile_id_version_provided(
        self,
    ) -> None:
        result = resolve_copilot_auth(
            agent_id="agent-1",
            auth={"git_hub_token": "tok", "profile_id": "p", "profile_version": "v1"},
            env=clean_env(),
            home_dir=fake_home_dir,
        )
        assert result["auth_mode"] == "gitHubToken"
        assert result["git_hub_token"] == "tok"
        assert result["auth_profile_id"] == "p"
        assert result["auth_profile_version"] == "v1"

    def test_accepts_legacy_top_level_profile_version_and_auth_profile_id_fallbacks(self) -> None:
        result = resolve_copilot_auth(
            agent_id="agent-1",
            auth={"git_hub_token": "tok"},
            auth_profile_id="legacy-p",
            profile_version="legacy-v1",
            env=clean_env(),
            home_dir=fake_home_dir,
        )
        assert result["auth_mode"] == "gitHubToken"
        assert result["auth_profile_id"] == "legacy-p"
        assert result["auth_profile_version"] == "legacy-v1"

    def test_throws_when_explicit_git_hub_token_without_profile_id_and_profile_version(
        self,
    ) -> None:
        with pytest.raises(ValueError) as exc_info:
            resolve_copilot_auth(
                agent_id="agent-1",
                auth={"git_hub_token": "tok"},
                env=clean_env(),
                home_dir=fake_home_dir,
            )
        assert str(exc_info.value) == COPILOT_TOKEN_PROFILE_ERROR

        with pytest.raises(ValueError) as exc_info:
            resolve_copilot_auth(
                agent_id="agent-1",
                auth={"git_hub_token": "tok", "profile_id": "p"},
                env=clean_env(),
                home_dir=fake_home_dir,
            )
        assert str(exc_info.value) == COPILOT_TOKEN_PROFILE_ERROR

        with pytest.raises(ValueError) as exc_info:
            resolve_copilot_auth(
                agent_id="agent-1",
                auth={"git_hub_token": "tok", "profile_version": "v"},
                env=clean_env(),
                home_dir=fake_home_dir,
            )
        assert str(exc_info.value) == COPILOT_TOKEN_PROFILE_ERROR

    def test_defaults_to_use_logged_in_user_when_no_auth_signal_at_all(self) -> None:
        result = resolve_copilot_auth(
            agent_id="agent-1",
            env=clean_env(),
            home_dir=fake_home_dir,
        )
        assert result["auth_mode"] == "useLoggedInUser"
        assert "git_hub_token" not in result


class TestResolveCopilotAuthContractResolved:
    def test_consumes_resolved_api_key_and_auth_profile_id_from_contract(self) -> None:
        result = resolve_copilot_auth(
            agent_id="agent-1",
            resolved_api_key="contract-token-xyz",
            auth_profile_id="github-copilot:main",
            env=clean_env(),
            home_dir=fake_home_dir,
        )
        assert result["auth_mode"] == "gitHubToken"
        assert result["git_hub_token"] == "contract-token-xyz"
        assert result["auth_profile_id"] == "github-copilot:main"
        assert result["auth_profile_version"] == token_fingerprint("contract-token-xyz")

    def test_synthesises_auth_profile_id_when_contract_resolved_token_has_no_profile_id(
        self,
    ) -> None:
        result = resolve_copilot_auth(
            agent_id="agent-1",
            resolved_api_key="contract-token-xyz",
            env=clean_env(),
            home_dir=fake_home_dir,
        )
        assert result["auth_mode"] == "gitHubToken"
        assert result["git_hub_token"] == "contract-token-xyz"
        assert result["auth_profile_id"] == "pi:resolved"
        assert result["auth_profile_version"] == token_fingerprint("contract-token-xyz")

    def test_auth_use_logged_in_user_true_takes_precedence_over_contract_resolved_api_key(
        self,
    ) -> None:
        result = resolve_copilot_auth(
            agent_id="agent-1",
            auth={"use_logged_in_user": True},
            resolved_api_key="should-be-ignored",
            auth_profile_id="p",
            env=clean_env(),
            home_dir=fake_home_dir,
        )
        assert result["auth_mode"] == "useLoggedInUser"
        assert "git_hub_token" not in result

    def test_explicit_auth_git_hub_token_takes_precedence_over_contract_resolved_api_key(
        self,
    ) -> None:
        result = resolve_copilot_auth(
            agent_id="agent-1",
            auth={"git_hub_token": "explicit", "profile_id": "p", "profile_version": "v1"},
            resolved_api_key="contract-should-be-ignored",
            auth_profile_id="contract-profile",
            env=clean_env(),
            home_dir=fake_home_dir,
        )
        assert result["auth_mode"] == "gitHubToken"
        assert result["git_hub_token"] == "explicit"
        assert result["auth_profile_id"] == "p"
        assert result["auth_profile_version"] == "v1"

    def test_contract_resolved_api_key_takes_precedence_over_env_fallback(self) -> None:
        result = resolve_copilot_auth(
            agent_id="agent-1",
            resolved_api_key="contract-token",
            auth_profile_id="p",
            env={
                "OPENCLAW_GITHUB_TOKEN": "env-should-be-ignored",
                "COPILOT_GITHUB_TOKEN": "copilot-env-should-be-ignored",
                "GH_TOKEN": "gh-env-should-be-ignored",
                "GITHUB_TOKEN": "github-env-should-be-ignored",
            },
            home_dir=fake_home_dir,
        )
        assert result["git_hub_token"] == "contract-token"
        assert result["auth_profile_id"] == "p"

    def test_falls_back_to_env_when_resolved_api_key_is_absent(self) -> None:
        result = resolve_copilot_auth(
            agent_id="agent-1",
            auth_profile_id="p",
            env={"GITHUB_TOKEN": "env-only"},
            home_dir=fake_home_dir,
        )
        assert result["git_hub_token"] == "env-only"
        assert result["auth_profile_id"] == "env:GITHUB_TOKEN"


class TestResolveCopilotAuthEnvFallbacks:
    def test_falls_back_to_github_token_with_synthesised_profile_id_and_fingerprint(self) -> None:
        result = resolve_copilot_auth(
            agent_id="agent-1",
            env={"GITHUB_TOKEN": "env-token-123"},
            home_dir=fake_home_dir,
        )
        assert result["auth_mode"] == "gitHubToken"
        assert result["git_hub_token"] == "env-token-123"
        assert result["auth_profile_id"] == "env:GITHUB_TOKEN"
        assert result["auth_profile_version"] == token_fingerprint("env-token-123")

    def test_openclaw_github_token_takes_precedence_over_github_token(self) -> None:
        result = resolve_copilot_auth(
            agent_id="agent-1",
            env={
                "OPENCLAW_GITHUB_TOKEN": "openclaw-tok",
                "GITHUB_TOKEN": "github-tok",
            },
            home_dir=fake_home_dir,
        )
        assert result["git_hub_token"] == "openclaw-tok"
        assert result["auth_profile_id"] == "env:OPENCLAW_GITHUB_TOKEN"
        assert result["auth_profile_version"] == token_fingerprint("openclaw-tok")

    def test_falls_back_to_copilot_github_token_with_synthesised_profile_id_and_fingerprint(
        self,
    ) -> None:
        result = resolve_copilot_auth(
            agent_id="agent-1",
            env={"COPILOT_GITHUB_TOKEN": "copilot-tok-123"},
            home_dir=fake_home_dir,
        )
        assert result["auth_mode"] == "gitHubToken"
        assert result["git_hub_token"] == "copilot-tok-123"
        assert result["auth_profile_id"] == "env:COPILOT_GITHUB_TOKEN"
        assert result["auth_profile_version"] == token_fingerprint("copilot-tok-123")

    def test_falls_back_to_gh_token_with_synthesised_profile_id_and_fingerprint(self) -> None:
        result = resolve_copilot_auth(
            agent_id="agent-1",
            env={"GH_TOKEN": "gh-tok-456"},
            home_dir=fake_home_dir,
        )
        assert result["auth_mode"] == "gitHubToken"
        assert result["git_hub_token"] == "gh-tok-456"
        assert result["auth_profile_id"] == "env:GH_TOKEN"
        assert result["auth_profile_version"] == token_fingerprint("gh-tok-456")

    def test_openclaw_github_token_takes_precedence_over_all_other_env_tokens(self) -> None:
        result = resolve_copilot_auth(
            agent_id="agent-1",
            env={
                "OPENCLAW_GITHUB_TOKEN": "openclaw-tok",
                "COPILOT_GITHUB_TOKEN": "copilot-tok",
                "GH_TOKEN": "gh-tok",
                "GITHUB_TOKEN": "github-tok",
            },
            home_dir=fake_home_dir,
        )
        assert result["git_hub_token"] == "openclaw-tok"
        assert result["auth_profile_id"] == "env:OPENCLAW_GITHUB_TOKEN"

    def test_copilot_github_token_takes_precedence_over_gh_token_and_github_token(self) -> None:
        result = resolve_copilot_auth(
            agent_id="agent-1",
            env={
                "COPILOT_GITHUB_TOKEN": "copilot-tok",
                "GH_TOKEN": "gh-tok",
                "GITHUB_TOKEN": "github-tok",
            },
            home_dir=fake_home_dir,
        )
        assert result["git_hub_token"] == "copilot-tok"
        assert result["auth_profile_id"] == "env:COPILOT_GITHUB_TOKEN"

    def test_gh_token_takes_precedence_over_github_token(self) -> None:
        result = resolve_copilot_auth(
            agent_id="agent-1",
            env={
                "GH_TOKEN": "gh-tok",
                "GITHUB_TOKEN": "github-tok",
            },
            home_dir=fake_home_dir,
        )
        assert result["git_hub_token"] == "gh-tok"
        assert result["auth_profile_id"] == "env:GH_TOKEN"

    def test_token_rotation_in_env_changes_the_pool_fingerprint(self) -> None:
        a = resolve_copilot_auth(
            agent_id="agent-1",
            env={"GITHUB_TOKEN": "v1"},
            home_dir=fake_home_dir,
        )
        b = resolve_copilot_auth(
            agent_id="agent-1",
            env={"GITHUB_TOKEN": "v2"},
            home_dir=fake_home_dir,
        )
        assert a["auth_profile_version"] != b["auth_profile_version"]

    def test_explicit_auth_use_logged_in_user_true_wins_over_env_tokens(self) -> None:
        result = resolve_copilot_auth(
            agent_id="agent-1",
            auth={"use_logged_in_user": True},
            env={"OPENCLAW_GITHUB_TOKEN": "env-tok"},
            home_dir=fake_home_dir,
        )
        assert result["auth_mode"] == "useLoggedInUser"

    def test_explicit_auth_git_hub_token_wins_over_env_tokens(self) -> None:
        result = resolve_copilot_auth(
            agent_id="agent-1",
            auth={"git_hub_token": "explicit", "profile_id": "p", "profile_version": "v"},
            env={"OPENCLAW_GITHUB_TOKEN": "env-tok"},
            home_dir=fake_home_dir,
        )
        assert result["auth_mode"] == "gitHubToken"
        assert result["git_hub_token"] == "explicit"
        assert result["auth_profile_id"] == "p"
        assert result["auth_profile_version"] == "v"

    def test_ignores_empty_string_env_tokens(self) -> None:
        result = resolve_copilot_auth(
            agent_id="agent-1",
            env={
                "GITHUB_TOKEN": "",
                "OPENCLAW_GITHUB_TOKEN": "",
                "COPILOT_GITHUB_TOKEN": "",
                "GH_TOKEN": "",
            },
            home_dir=fake_home_dir,
        )
        assert result["auth_mode"] == "useLoggedInUser"


class TestResolveCopilotAuthDefaultsWiring:
    def test_uses_process_env_when_env_is_not_injected(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("OPENCLAW_GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("COPILOT_GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("GH_TOKEN", raising=False)
        monkeypatch.delenv("OPENCLAW_HOME", raising=False)
        monkeypatch.setenv("GITHUB_TOKEN", "from-process-env")
        result = resolve_copilot_auth(agent_id="agent-1", home_dir=fake_home_dir)
        assert result["auth_mode"] == "gitHubToken"
        assert result["git_hub_token"] == "from-process-env"

    def test_uses_os_homedir_when_home_dir_is_not_injected(self) -> None:
        result = resolve_copilot_auth(agent_id="agent-1")
        suffix = str(Path(".openclaw") / "agents" / "agent-1" / "copilot")
        assert result["copilot_home"].endswith(suffix)

    def test_falls_back_to_process_cwd_if_home_dir_throws(self) -> None:
        def broken_home_dir() -> str:
            raise RuntimeError("no home")

        result = resolve_copilot_auth(
            agent_id="agent-1",
            env=clean_env(),
            home_dir=broken_home_dir,
        )
        suffix = str(Path(".openclaw") / "agents" / "agent-1" / "copilot")
        assert suffix in result["copilot_home"]
