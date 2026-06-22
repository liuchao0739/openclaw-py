"""Session extension that prunes stale context blocks before model calls."""

from __future__ import annotations

import time

from openclaw.agents.agent_hooks.context_pruning.pruner import prune_context_messages
from openclaw.agents.agent_hooks.context_pruning.runtime import get_context_pruning_runtime
from openclaw.agents.sessions import ContextEvent, ExtensionAPI, ExtensionContext


def register_context_pruning_extension(api: ExtensionAPI) -> None:
    def on_context(event: ContextEvent, ctx: ExtensionContext) -> dict | None:
        runtime = get_context_pruning_runtime(ctx.session_manager)
        if runtime is None:
            return None

        if runtime.settings.mode == "cache-ttl":
            ttl_ms = runtime.settings.ttl_ms
            last_touch = runtime.last_cache_touch_at
            if not last_touch or ttl_ms <= 0:
                return None
            if ttl_ms > 0 and (time.time() * 1000) - last_touch < ttl_ms:
                return None

        next_messages = prune_context_messages(
            messages=event.messages,
            settings=runtime.settings,
            ctx=ctx,
            is_tool_prunable=runtime.is_tool_prunable,
            context_window_tokens_override=runtime.context_window_tokens,
            drop_thinking_blocks_for_estimate=runtime.drop_thinking_blocks,
        )

        if next_messages is event.messages:
            return None

        if runtime.settings.mode == "cache-ttl":
            runtime.last_cache_touch_at = int(time.time() * 1000)

        return {"messages": next_messages}

    api.on("context", on_context)