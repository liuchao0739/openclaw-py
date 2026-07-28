from __future__ import annotations

from typing import Any


def create_plugin_hook_runner(
    hooks: list[Any] | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "hooks": hooks or [],
        "context": context or {},
        "results": [],
    }


def run_plugin_hooks(
    lifecycle: str,
    hooks: list[Any],
    context: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for hook in hooks:
        handler = None
        if isinstance(hook, dict):
            handler = hook.get(lifecycle)
        else:
            handler = getattr(hook, lifecycle, None)
        if not handler or not callable(handler):
            continue
        try:
            result = handler(context or {})
            results.append({
                "hookId": hook.get("id", "unknown") if isinstance(hook, dict) else str(hook),
                "result": result,
            })
        except Exception as e:
            results.append({
                "hookId": hook.get("id", "unknown") if isinstance(hook, dict) else str(hook),
                "error": str(e),
            })
    return results
