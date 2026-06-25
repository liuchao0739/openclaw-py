"""Test fixture helpers for constructing ACP runtime session metadata."""

from __future__ import annotations

import time
from typing import Any


def create_acp_test_config(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    """Create a test ACP config with sensible defaults."""
    config: dict[str, Any] = {
        "acp": {
            "enabled": True,
            "stream": {
                "coalesceIdleMs": 0,
                "maxChunkChars": 64,
            },
        },
    }
    if overrides:
        config.update(overrides)
    return config


def create_acp_session_meta(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    """Create test ACP session metadata with sensible defaults."""
    now = int(time.time() * 1000)
    meta: dict[str, Any] = {
        "backend": "acpx",
        "agent": "codex",
        "runtimeSessionName": "runtime:1",
        "mode": "persistent",
        "state": "idle",
        "lastActivityAt": now,
        "identity": {
            "state": "resolved",
            "acpxSessionId": "acpx-session-1",
            "source": "status",
            "lastUpdatedAt": now,
        },
    }
    if overrides:
        meta.update(overrides)
    return meta
