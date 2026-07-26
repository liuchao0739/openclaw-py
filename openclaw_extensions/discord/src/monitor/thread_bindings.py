"""Discord plugin module implements thread bindings behavior."""

from __future__ import annotations

from openclaw_extensions.discord.src.monitor.thread_bindings_lifecycle import (
    auto_bind_spawned_discord_subagent,
    list_thread_bindings_by_session_key,
    unbind_thread_bindings_by_session_key,
)
from openclaw_extensions.discord.src.monitor.thread_bindings_types import (
    ThreadBindingRecord,
    ThreadBindingTargetKind,
)

__all__ = [
    "ThreadBindingRecord",
    "ThreadBindingTargetKind",
    "auto_bind_spawned_discord_subagent",
    "list_thread_bindings_by_session_key",
    "unbind_thread_bindings_by_session_key",
]
