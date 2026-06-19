"""Tests for openclaw.infra.paths."""

from __future__ import annotations

from openclaw.infra.paths import resolve_config_path, resolve_state_dir


def test_resolve_state_dir_override() -> None:
    env = {"OPENCLAW_STATE_DIR": "/tmp/custom-state"}
    assert resolve_state_dir(env, homedir=lambda: "/home/user") == "/tmp/custom-state"


def test_resolve_state_dir_default() -> None:
    env: dict[str, str] = {}
    assert resolve_state_dir(env, homedir=lambda: "/home/user") == "/home/user/.openclaw"


def test_resolve_state_dir_fast_test_mode() -> None:
    env = {"OPENCLAW_TEST_FAST": "1"}
    assert resolve_state_dir(env, homedir=lambda: "/home/user") == "/home/user/.openclaw"


def test_resolve_config_path() -> None:
    env = {"OPENCLAW_STATE_DIR": "/tmp/state"}
    assert resolve_config_path(env) == "/tmp/state/openclaw.json"
