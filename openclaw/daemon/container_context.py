"""Detects whether a daemon was launched by OpenClaw's container-aware service wrapper.

Mirrors src/daemon/container-context.ts.
"""

from __future__ import annotations

from typing import Any, Mapping


def _normalize_optional_string(value: Any) -> str | None:
    if isinstance(value, str):
        s = value.strip()
        return s or None
    return None


def resolve_daemon_container_context(
    env: Mapping[str, Any] | None = None,
) -> str | None:
    """Resolve the daemon container hint exposed by managed service environments."""
    if env is None:
        import os
        env = os.environ
    return (
        _normalize_optional_string(env.get("OPENCLAW_CONTAINER_HINT"))
        or _normalize_optional_string(env.get("OPENCLAW_CONTAINER"))
        or None
    )
