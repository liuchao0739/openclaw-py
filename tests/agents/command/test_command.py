"""Tests agents/command partial port."""

import os

from openclaw.agents.command import (
    build_explicit_session_id_session_key,
    resolve_agent_run_context,
    resolve_claude_cli_project_dir_for_workspace,
    resolve_stored_session_key_for_session_id,
    sanitize_claude_cli_project_key,
)


def test_build_explicit_session_key():
    assert build_explicit_session_id_session_key(session_id="abc", agent_id="main") == (
        "agent:main:explicit:abc"
    )


def test_resolve_stored_session_key_tiebreak():
    store = {
        "agent:main:main": {"sessionId": "sid", "updatedAt": 10},
        "agent:other:main": {"sessionId": "sid", "updatedAt": 20},
    }
    r = resolve_stored_session_key_for_session_id(
        session_store=store,
        store_path="/stores/main.json",
        session_id="sid",
    )
    assert r["sessionKey"] == "agent:other:main"


def test_resolve_agent_run_context():
    ctx = resolve_agent_run_context(
        {
            "messageChannel": "telegram",
            "to": " chat123 ",
            "threadId": 99,
        }
    )
    assert ctx["messageChannel"] == "telegram"
    assert ctx["currentChannelId"] == "chat123"
    assert ctx["currentThreadTs"] == "99"


def test_claude_project_dir():
    path = resolve_claude_cli_project_dir_for_workspace(
        workspace_dir="/tmp/my workspace",
        home_dir="/home/u",
    )
    assert path.startswith("/home/u/.claude/projects/")
    assert sanitize_claude_cli_project_key("hello world") == "hello-world"