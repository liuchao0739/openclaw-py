"""Reads channel plugin output/threading policy for isolated cron delivery.

Mirrors src/cron/isolated-agent/channel-output-policy.ts. The channel plugin
runtime is lazily imported; tests inject a loader via the module-level
``_channel_plugin_loader`` override.
"""

from __future__ import annotations

from typing import Any, Callable, Awaitable


def _normalize_optional_lowercase_string(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        s = value.strip().lower()
        return s or None
    return None


# Override in tests to stub the channel plugin runtime loader.
_channel_plugin_loader: Callable[[], Awaitable[Any]] | None = None


async def _load_channel_plugin_runtime() -> Any:
    if _channel_plugin_loader is not None:
        return await _channel_plugin_loader()
    raise NotImplementedError("channel plugin runtime not available in this build")


async def resolve_cron_channel_output_policy(
    channel: Any,
    opts: dict[str, Any] | None = None,
) -> dict[str, bool]:
    """Resolve channel-specific cron output preferences from loaded channel plugins."""
    delivery_requested = bool((opts or {}).get("deliveryRequested"))
    channel_id = _normalize_optional_lowercase_string(channel)
    if not channel_id:
        return {"prefer_final_assistant_visible_text": not delivery_requested}
    try:
        runtime = await _load_channel_plugin_runtime()
    except NotImplementedError:
        return {"prefer_final_assistant_visible_text": False}
    get_channel_plugin = getattr(runtime, "get_channel_plugin", None) or getattr(
        runtime, "getChannelPlugin", None
    )
    if get_channel_plugin is None:
        return {"prefer_final_assistant_visible_text": False}
    plugin = get_channel_plugin(channel_id)
    outbound = getattr(plugin, "outbound", None) if plugin else None
    if outbound is None and isinstance(plugin, dict):
        outbound = plugin.get("outbound")
    prefer = getattr(outbound, "preferFinalAssistantVisibleText", None) if outbound else None
    if prefer is None and isinstance(outbound, dict):
        prefer = outbound.get("preferFinalAssistantVisibleText")
    return {"prefer_final_assistant_visible_text": prefer is True}


async def resolve_current_channel_target(
    params: dict[str, Any],
) -> str | None:
    """Resolve the provider-specific current-thread target for a delivery address."""
    to = params.get("to")
    if not to:
        return None
    channel_id = _normalize_optional_lowercase_string(params.get("channel"))
    if not channel_id:
        return to
    try:
        runtime = await _load_channel_plugin_runtime()
    except NotImplementedError:
        return to
    get_channel_plugin = getattr(runtime, "get_channel_plugin", None) or getattr(
        runtime, "getChannelPlugin", None
    )
    if get_channel_plugin is None:
        return to
    plugin = get_channel_plugin(channel_id)
    threading = getattr(plugin, "threading", None) if plugin else None
    if threading is None and isinstance(plugin, dict):
        threading = plugin.get("threading")
    resolver = getattr(threading, "resolveCurrentChannelId", None) if threading else None
    if resolver is None and isinstance(threading, dict):
        resolver = threading.get("resolveCurrentChannelId")
    if resolver is None:
        return to
    result = resolver({"to": to, "threadId": params.get("threadId")})
    return result if result is not None else to
