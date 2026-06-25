"""Tests for commands/onboard-non-interactive — config write and remote setup."""

from __future__ import annotations

from openclaw.commands.onboard_non_interactive import (
    commit_non_interactive_onboard_config,
    run_non_interactive_remote_setup,
)


class TestCommitNonInteractiveOnboardConfig:
    async def test_basic_commit(self):
        result = await commit_non_interactive_onboard_config(
            next_config={"gateway": {"mode": "remote"}},
            base_config={},
        )
        assert result is not None

    async def test_with_reset(self):
        result = await commit_non_interactive_onboard_config(
            next_config={"test": True},
            base_config={},
            reset=True,
        )
        assert result is not None


class TestRunNonInteractiveRemoteSetup:
    async def test_missing_remote_url(self):
        result = await run_non_interactive_remote_setup(
            opts={},
            runtime={"error": lambda m: None},
        )
        assert result["ok"] is False
        assert "Missing" in result["error"]

    async def test_successful_setup(self):
        logs: list[str] = []
        result = await run_non_interactive_remote_setup(
            opts={"remoteUrl": "ws://127.0.0.1:3000", "remoteToken": "secret"},
            runtime={"log": lambda m: logs.append(m), "error": lambda m: None},
            base_config={},
        )
        assert result["ok"] is True
        assert result["mode"] == "remote"
        assert result["remoteUrl"] == "ws://127.0.0.1:3000"
        assert result["auth"] == "token"
        assert any("ws://127.0.0.1:3000" in log for log in logs)

    async def test_no_token_auth(self):
        result = await run_non_interactive_remote_setup(
            opts={"remoteUrl": "ws://localhost:3000"},
            runtime={"log": lambda m: None, "error": lambda m: None},
            base_config={},
        )
        assert result["auth"] == "none"

    async def test_json_output(self):
        result = await run_non_interactive_remote_setup(
            opts={"remoteUrl": "ws://localhost:3000", "json": True},
            runtime={},
            base_config={},
        )
        assert result["ok"] is True
        assert result.get("mode") == "remote"
