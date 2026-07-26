"""Browser setup entry that auto-enables the Browser plugin from config references."""

from __future__ import annotations

from typing import Any

from openclaw.packages.normalization_core import is_record, normalize_optional_lowercase_string
from openclaw.plugin_sdk.plugin_entry import OpenClawPluginApi, define_plugin_entry


def _list_contains_browser(value: Any) -> bool:
    if not isinstance(value, list):
        return False
    return any(normalize_optional_lowercase_string(entry) == "browser" for entry in value)


def _tool_policy_references_browser(value: Any) -> bool:
    if not is_record(value):
        return False
    return _list_contains_browser(value.get("allow")) or _list_contains_browser(
        value.get("alsoAllow")
    )


def _has_browser_tool_reference(config: Any) -> bool:
    tools = config.get("tools") if isinstance(config, dict) else getattr(config, "tools", None)
    if _tool_policy_references_browser(tools):
        return True
    agent_list = config.get("agents", {}).get("list") if isinstance(config, dict) else None
    if agent_list is None and not isinstance(config, dict):
        agents = getattr(config, "agents", None)
        agent_list = getattr(agents, "list", None) if agents is not None else None
    if not isinstance(agent_list, list):
        return False
    return any(
        is_record(entry) and _tool_policy_references_browser(entry.get("tools"))
        for entry in agent_list
    )


def _register(api: OpenClawPluginApi) -> None:
    def probe(ctx: dict[str, Any]) -> str | None:
        config = ctx.get("config")
        if not isinstance(config, dict):
            return None
        browser = config.get("browser")
        plugins = config.get("plugins")
        plugins_entries = plugins.get("entries") if is_record(plugins) else None
        if isinstance(browser, dict) and browser.get("enabled") is False:
            return None
        if (
            isinstance(plugins_entries, dict)
            and isinstance(plugins_entries.get("browser"), dict)
            and plugins_entries["browser"].get("enabled") is False
        ):
            return None
        if "browser" in config:
            return "browser configured"
        if isinstance(plugins_entries, dict) and "browser" in plugins_entries:
            return "browser plugin configured"
        if _has_browser_tool_reference(config):
            return "browser tool referenced"
        return None

    api.register_auto_enable_probe(probe)  # type: ignore[attr-defined]


default = define_plugin_entry(
    id="browser",
    name="Browser Setup",
    description="Lightweight Browser setup hooks",
    register=_register,
)
