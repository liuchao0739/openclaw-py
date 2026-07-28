from __future__ import annotations

from typing import Any


def build_host_hooks(
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "beforeAgentStart": [],
        "beforeToolCall": [],
        "beforeToolCallResult": [],
        "beforeAgentReply": [],
        "beforeAgentFinalize": [],
        "config": config or {},
    }


def register_host_hook(
    host_hooks: dict[str, Any],
    lifecycle: str,
    hook: Any,
) -> dict[str, Any]:
    hooks = host_hooks.setdefault(lifecycle, [])
    hooks.append(hook)
    return host_hooks
