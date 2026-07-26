"""Diffs plugin module implements plugin behavior."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from openclaw.config.models import OpenClawConfig
from openclaw.packages.normalization_core import is_record
from openclaw_extensions.diffs.api import OpenClawPluginApi, resolve_preferred_openclaw_tmp_dir

DIFFS_LANGUAGE_PACK_PLUGIN_ID = "diffs-language-pack"


def register_diffs_plugin(api: OpenClawPluginApi) -> None:
    from openclaw_extensions.diffs.src.config import (
        resolve_diffs_plugin_defaults,
        resolve_diffs_plugin_security,
        resolve_diffs_plugin_viewer_base_url,
    )
    from openclaw_extensions.diffs.src.http import create_diffs_http_handler
    from openclaw_extensions.diffs.src.prompt_guidance import DIFFS_AGENT_GUIDANCE
    from openclaw_extensions.diffs.src.store import DiffArtifactStore
    from openclaw_extensions.diffs.src.tool import create_diffs_tool

    store = DiffArtifactStore(
        root_dir=str(Path(resolve_preferred_openclaw_tmp_dir()) / "openclaw-diffs"),
        logger=api.logger,
    )

    def resolve_current_plugin_config() -> dict[str, Any]:
        plugin_config = getattr(api, "plugin_config", None)
        if is_record(plugin_config):
            return dict(plugin_config)
        return {}

    def resolve_current_access_config() -> dict[str, Any]:
        current_config = _resolve_current_config(api)
        plugin_config = resolve_current_plugin_config()
        security = resolve_diffs_plugin_security(plugin_config)
        return {
            "allow_remote_viewer": security["allowRemoteViewer"],
            "trusted_proxies": _gateway_field(current_config, "trustedProxies"),
            "allow_real_ip_fallback": _gateway_field(current_config, "allowRealIpFallback") is True,
        }

    initial_access_config = resolve_current_access_config()

    api.register_tool(
        lambda ctx: create_diffs_tool(
            api=api,
            store=store,
            defaults=resolve_diffs_plugin_defaults(resolve_current_plugin_config()),
            viewer_base_url=resolve_diffs_plugin_viewer_base_url(resolve_current_plugin_config()),
            language_pack_available=resolve_diffs_language_pack_availability(api),
            context=ctx,
        ),
        {"name": "diffs"},
    )
    api.register_http_route(
        {
            "path": "/plugins/diffs",
            "auth": "plugin",
            "match": "prefix",
            "handler": create_diffs_http_handler(
                store=store,
                logger=api.logger,
                allow_remote_viewer=initial_access_config["allow_remote_viewer"],
                trusted_proxies=initial_access_config["trusted_proxies"],
                allow_real_ip_fallback=initial_access_config["allow_real_ip_fallback"],
                resolve_access_config=resolve_current_access_config,
            ),
        }
    )
    api.on(
        "before_prompt_build",
        lambda: {"prependSystemContext": DIFFS_AGENT_GUIDANCE},
    )


def resolve_diffs_language_pack_availability(api: OpenClawPluginApi) -> bool:
    current_config = _resolve_current_config(api)
    plugins = _read_plugins_config(current_config)
    if plugins is None:
        return _has_sibling_language_pack_runtime(getattr(api, "root_dir", None))
    if plugins.get("enabled") is False:
        return False
    deny = plugins.get("deny")
    if isinstance(deny, list) and DIFFS_LANGUAGE_PACK_PLUGIN_ID in deny:
        return False
    allow = plugins.get("allow")
    if isinstance(allow, list) and DIFFS_LANGUAGE_PACK_PLUGIN_ID not in allow:
        return False
    entries = plugins.get("entries")
    if isinstance(entries, dict):
        entry = entries.get(DIFFS_LANGUAGE_PACK_PLUGIN_ID)
        if isinstance(entry, dict) and entry.get("enabled") is False:
            return False
    return _has_sibling_language_pack_runtime(getattr(api, "root_dir", None))


def _resolve_current_config(api: OpenClawPluginApi) -> OpenClawConfig | dict[str, Any]:
    runtime = getattr(api, "runtime", None)
    config = getattr(runtime, "config", None) if runtime is not None else None
    current = getattr(config, "current", None) if config is not None else None
    if callable(current):
        resolved = current()
        if resolved is not None:
            return resolved
    fallback = getattr(api, "config", None)
    if fallback is not None:
        return fallback
    return {}


def _read_plugins_config(config: OpenClawConfig | dict[str, Any]) -> dict[str, Any] | None:
    plugins = getattr(config, "plugins", None)
    if plugins is None and isinstance(config, dict):
        plugins = config.get("plugins")
    return plugins if is_record(plugins) else None


def _gateway_field(config: OpenClawConfig | dict[str, Any], key: str) -> Any:
    gateway = getattr(config, "gateway", None)
    if gateway is None and isinstance(config, dict):
        gateway = config.get("gateway")
    if is_record(gateway):
        return gateway.get(key)
    return getattr(gateway, key, None) if gateway is not None else None


def _has_sibling_language_pack_runtime(root_dir: str | None) -> bool:
    if not root_dir:
        return False
    parent = Path(root_dir).parent
    candidate_roots = (
        parent / DIFFS_LANGUAGE_PACK_PLUGIN_ID,
        parent / "diffs_language_pack",
    )
    runtime_paths = (
        ("assets", "viewer-runtime.js"),
        ("dist", "assets", "viewer-runtime.js"),
    )
    for candidate_root in candidate_roots:
        if not (candidate_root / "openclaw.plugin.json").is_file():
            continue
        if any((candidate_root.joinpath(*parts)).is_file() for parts in runtime_paths):
            return True
    return False
