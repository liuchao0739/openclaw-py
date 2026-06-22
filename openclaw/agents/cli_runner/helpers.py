"""Shared helpers for CLI runner queue keys and serialization."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Awaitable, Callable
from typing import TypeVar

from openclaw.infra.keyed_async_queue import KeyedAsyncQueue

T = TypeVar("T")

_CLI_RUN_QUEUE = KeyedAsyncQueue()


def enqueue_cli_run(key: str, task: Callable[[], Awaitable[T]]) -> Awaitable[T]:
    return _CLI_RUN_QUEUE.enqueue(key, task)


def build_claude_owner_key(
    *,
    agent_account_id: str | None = None,
    agent_id: str | None = None,
    auth_profile_id: str | None = None,
    session_id: str | None = None,
    session_key: str | None = None,
) -> str:
    payload = json.dumps(
        {
            "agentAccountId": agent_account_id,
            "agentId": agent_id,
            "authProfileId": auth_profile_id,
            "sessionId": session_id,
            "sessionKey": session_key,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _is_claude_cli_provider(provider_id: str) -> bool:
    return (provider_id or "").strip().lower() == "claude-cli"


def resolve_cli_run_queue_key(
    *,
    backend_id: str,
    live_session: str | None = None,
    serialize: bool | None = None,
    run_id: str,
    workspace_dir: str,
    cli_session_id: str | None = None,
    owner_key: str | None = None,
) -> str:
    requires_live = _is_claude_cli_provider(backend_id) and live_session == "claude-stdio"
    if serialize is False and not requires_live:
        return f"{backend_id}:{run_id}"
    if _is_claude_cli_provider(backend_id):
        owner = (owner_key or "").strip()
        if requires_live and owner:
            return f"{backend_id}:owner:{owner}"
        session_id = (cli_session_id or "").strip()
        if session_id:
            return f"{backend_id}:session:{session_id}"
        if owner:
            return f"{backend_id}:owner:{owner}"
        workspace = workspace_dir.strip()
        if workspace:
            return f"{backend_id}:workspace:{workspace}"
    return backend_id