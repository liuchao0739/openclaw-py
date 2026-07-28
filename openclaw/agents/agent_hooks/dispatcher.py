from __future__ import annotations

from typing import Any

from openclaw.agents.agent_hooks.events import AgentHookEvent, AgentHookLifecycle


def dispatch_agent_hook(
    lifecycle: str,
    context: dict[str, Any],
    hooks: list[Any] | None = None,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for hook in hooks or []:
        handler = hook.get(lifecycle) if isinstance(hook, dict) else getattr(hook, lifecycle, None)
        if not handler:
            continue
        try:
            result = handler(context) if callable(handler) else None
            results.append({
                "hookId": hook.get("id", "unknown") if isinstance(hook, dict) else str(hook),
                "lifecycle": lifecycle,
                "result": result,
            })
        except Exception as e:
            results.append({
                "hookId": hook.get("id", "unknown") if isinstance(hook, dict) else str(hook),
                "lifecycle": lifecycle,
                "error": str(e),
            })
    return results


def create_agent_hook_dispatcher(hooks: list[Any] | None = None) -> dict[str, Any]:
    def _dispatch(lifecycle: str, context: dict[str, Any]) -> list[dict[str, Any]]:
        return dispatch_agent_hook(lifecycle, context, hooks)

    return {
        "dispatch": _dispatch,
        "hooks": hooks or [],
    }
