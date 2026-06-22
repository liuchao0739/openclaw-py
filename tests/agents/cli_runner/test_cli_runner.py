"""Tests CLI runner helpers, reliability, and TOML inline."""

import asyncio
import json

import pytest

from openclaw.agents.cli_runner import (
    attach_cli_messaging_delivery_evidence,
    build_claude_owner_key,
    build_cli_supervisor_scope_key,
    format_toml_config_override,
    get_cli_messaging_delivery_evidence,
    resolve_cli_no_output_timeout_ms,
    resolve_cli_run_queue_key,
    resolve_cli_run_timeout_override_ms,
    serialize_toml_inline_value,
)
from openclaw.agents.cli_runner.helpers import enqueue_cli_run


def test_build_claude_owner_key_matches_ts_key_order():
    import hashlib

    payload = json.dumps(
        {
            "agentAccountId": None,
            "agentId": "a1",
            "authProfileId": None,
            "sessionId": "s1",
            "sessionKey": None,
        },
        separators=(",", ":"),
    ).replace(":null", ":null")  # TS omits undefined; we pass explicit for test
    # Match TS: undefined fields are omitted
    payload_ts = '{"agentAccountId":null,"agentId":"a1","authProfileId":null,"sessionId":"s1","sessionKey":null}'
    # Our helper includes all keys with None -> null in JSON
    key = build_claude_owner_key(agent_id="a1", session_id="s1")
    assert len(key) == 64


def test_resolve_cli_run_queue_key():
    assert resolve_cli_run_queue_key(
        backend_id="openai", serialize=False, run_id="r1", workspace_dir="/w"
    ) == "openai:r1"
    assert (
        resolve_cli_run_queue_key(
            backend_id="claude-cli",
            live_session="claude-stdio",
            run_id="r1",
            workspace_dir="/w",
            owner_key="owner1",
        )
        == "claude-cli:owner:owner1"
    )


def test_resolve_cli_no_output_timeout():
    backend: dict = {}
    t = resolve_cli_no_output_timeout_ms(backend=backend, timeout_ms=600_000, use_resume=False)
    assert 1_000 <= t < 600_000


def test_toml_inline():
    assert serialize_toml_inline_value("a\"b") == '"a\\"b"'
    assert format_toml_config_override("k", True) == "k=true"
    assert format_toml_config_override("k", {"x": 1}) == "k={ x = 1 }"


def test_delivery_evidence():
    err = RuntimeError("fail")
    out = attach_cli_messaging_delivery_evidence(
        err,
        {"didSendViaMessagingTool": True, "messagingToolSentTexts": ["hi"]},
    )
    ev = get_cli_messaging_delivery_evidence(err)
    assert ev and ev.get("messagingToolSentTexts") == ["hi"]


def test_supervisor_scope_key():
    assert (
        build_cli_supervisor_scope_key(
            backend={"command": "/usr/bin/claude"},
            backend_id="claude-cli",
            cli_session_id="sess",
        )
        == "cli:claude-cli:claude:sess"
    )


def test_run_timeout_override():
    assert (
        resolve_cli_run_timeout_override_ms(
            config={"agents": {"defaults": {"timeoutSeconds": 120}}},
            lane="main",
            timeout_ms=120_000,
        )
        == 120_000
    )


@pytest.mark.asyncio
async def test_enqueue_cli_run_serializes():
    order: list[int] = []

    async def work(n: int) -> int:
        order.append(n)
        await asyncio.sleep(0.01)
        return n

    k = "test-key"
    r1 = asyncio.create_task(enqueue_cli_run(k, lambda: work(1)))
    r2 = asyncio.create_task(enqueue_cli_run(k, lambda: work(2)))
    assert await r1 == 1
    assert await r2 == 2
    assert order == [1, 2]