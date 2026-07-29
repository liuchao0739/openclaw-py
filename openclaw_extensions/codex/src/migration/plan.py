import os
from pathlib import Path

from openclaw.plugin_sdk.migration import (
    create_migration_item,
    create_migration_manual_item,
    has_migration_config_patch_conflict,
    MIGRATION_REASON_TARGET_EXISTS,
    read_migration_config_path,
    summarize_migration_items,
)
from openclaw.plugin_sdk.string_coerce_runtime import as_boolean, is_record

from ..app_server.config import CODEX_PLUGINS_MARKETPLACE_NAME
from .auth import build_codexAuth_items as build_codex_auth_items
from .helpers import exists, sanitize_name
from .source import codex_plugin_migration_subscription_warning, discover_codex_source, has_codex_source
from .targets import resolve_codex_migration_targets

CODEX_PLUGIN_CONFIG_ITEM_ID = "config:codex-plugins"
CODEX_PLUGIN_CONFIG_PATH = ["plugins", "entries", "codex"]
CODEX_PLUGIN_ENABLED_PATH = ["plugins", "entries", "codex", "enabled"]
CODEX_PLUGIN_NATIVE_CONFIG_PATH = ["plugins", "entries", "codex", "config", "codexPlugins"]
MIGRATION_REASON_PLUGIN_EXISTS = "plugin exists"
CODEX_PLUGIN_SOURCE_APP_VERIFICATION_UNVERIFIED = "not_run"


class Error(Exception):
    pass


def _unique_skill_name(skill: dict, counts: dict) -> str:
    base = sanitize_name(skill["name"]) or "codex-skill"
    if (counts.get(base) or 0) <= 1:
        return base
    parent = sanitize_name(Path(skill["source"]).parent.name)
    return sanitize_name("-".join([p for p in ["codex", parent, base] if p])) or base


async def _build_skill_items(params: dict):
    base_counts: dict = {}
    for skill in params["skills"]:
        base = sanitize_name(skill["name"]) or "codex-skill"
        base_counts[base] = base_counts.get(base, 0) + 1
    resolved_counts: dict = {}
    planned = []
    for skill in params["skills"]:
        name = _unique_skill_name(skill, base_counts)
        resolved_counts[name] = resolved_counts.get(name, 0) + 1
        planned.append({"skill": skill, "name": name, "target": str(Path(params["workspaceDir"], "skills", name))})
    items = []
    for item in planned:
        collides = (resolved_counts.get(item["name"]) or 0) > 1
        target_exists = await exists(item["target"])
        items.append(create_migration_item({
            "id": f"skill:{item['name']}",
            "kind": "skill",
            "action": "copy",
            "source": item["skill"]["source"],
            "target": item["target"],
            "status": "conflict" if collides else ("conflict" if target_exists and not params.get("overwrite") else "planned"),
            "reason": ("multiple Codex skills normalize to \"{name}\"".format(name=item["name"]) if collides else (MIGRATION_REASON_TARGET_EXISTS if target_exists and not params.get("overwrite") else None)),
            "message": f"Copy {item['skill']['sourceLabel']} into this OpenClaw agent workspace.",
            "details": {"skillName": item["name"], "sourceLabel": item["skill"]["sourceLabel"]},
        }))
    return items


def _unique_plugin_config_key(plugin: dict, counts: dict, used_counts: dict) -> str:
    base = sanitize_name(plugin.get("pluginName") or plugin["name"]) or "codex-plugin"
    total = counts.get(base) or 0
    if total <= 1:
        return base
    next_count = (used_counts.get(base) or 0) + 1
    used_counts[base] = next_count
    return sanitize_name(f"{base}-{next_count}") or base


def _read_existing_codex_plugin_entries(config) -> dict:
    entries = read_migration_config_path(config, [*CODEX_PLUGIN_NATIVE_CONFIG_PATH, "plugins"])
    return entries if isinstance(entries, dict) else {}


def _has_existing_codex_plugin_entry(existing_entries: dict, config_key: str, plugin_name: str, next_entry: dict) -> bool:
    existing_entry = existing_entries.get(config_key)
    if existing_entry is not None:
        return not _is_legacy_destructive_policy_repair(existing_entry, next_entry)
    for entry in existing_entries.values():
        if isinstance(entry, dict) and entry.get("pluginName") == plugin_name:
            return True
    return False


def _is_legacy_destructive_policy_repair(existing, next_entry: dict) -> bool:
    existing_entry = existing if isinstance(existing, dict) else None
    if not existing_entry or existing_entry.get("allow_destructive_actions") != "on-request" or next_entry.get("allow_destructive_actions") != "auto":
        return False
    normalized_existing = {**existing_entry, "allow_destructive_actions": "auto"}
    return len(normalized_existing) == len(next_entry) and all(next_entry.get(k) == v for k, v in normalized_existing.items())


def _is_legacy_destructive_policy_config_entry_repair(existing, plugin_name: str) -> bool:
    existing_entry = existing if isinstance(existing, dict) else None
    return bool(existing_entry and existing_entry.get("allow_destructive_actions") == "on-request" and existing_entry.get("pluginName") == plugin_name)


def _build_plugin_items(ctx: dict, plugins) -> list:
    base_counts: dict = {}
    for plugin in plugins:
        if not plugin.get("migratable"):
            continue
        base = sanitize_name(plugin.get("pluginName") or plugin["name"]) or "codex-plugin"
        base_counts[base] = base_counts.get(base, 0) + 1
    existing_plugin_entries = _read_existing_codex_plugin_entries(ctx["config"])
    used_counts: dict = {}
    manual_index = 0
    items = []
    for plugin in plugins:
        if plugin.get("migratable") and plugin.get("marketplaceName") == CODEX_PLUGINS_MARKETPLACE_NAME and plugin.get("pluginName"):
            config_key = _unique_plugin_config_key(plugin, base_counts, used_counts)
            planned_entry = {"enabled": True, "marketplaceName": CODEX_PLUGINS_MARKETPLACE_NAME, "pluginName": plugin["pluginName"]}
            if _is_legacy_destructive_policy_config_entry_repair(existing_plugin_entries.get(config_key), plugin["pluginName"]):
                planned_entry["allow_destructive_actions"] = "auto"
            conflict = not ctx.get("overwrite") and _has_existing_codex_plugin_entry(existing_plugin_entries, config_key, plugin["pluginName"], planned_entry)
            details = {"configKey": config_key, "marketplaceName": CODEX_PLUGINS_MARKETPLACE_NAME, "pluginName": plugin["pluginName"], "sourceInstalled": plugin.get("installed") is True, "sourceEnabled": plugin.get("enabled") is True}
            if planned_entry.get("allow_destructive_actions") == "auto":
                details["allowDestructiveActions"] = "auto"
            if plugin.get("apps") and not _should_verify_plugin_apps(ctx):
                details["sourceAppVerification"] = CODEX_PLUGIN_SOURCE_APP_VERIFICATION_UNVERIFIED
            items.append(create_migration_item({
                "id": f"plugin:{config_key}",
                "kind": "plugin",
                "action": "install",
                "status": "conflict" if conflict else "planned",
                "reason": MIGRATION_REASON_PLUGIN_EXISTS if conflict else None,
                "source": plugin["source"],
                "target": f"plugins.entries.codex.config.codexPlugins.plugins.{config_key}",
                "message": f"Install Codex plugin \"{plugin['pluginName']}\" in the OpenClaw-managed Codex app-server runtime.",
                "details": details,
            }))
            continue
        manual_index += 1
        if plugin.get("migrationBlock") and plugin.get("pluginName"):
            details = {"pluginName": plugin["pluginName"], "marketplaceName": CODEX_PLUGINS_MARKETPLACE_NAME}
            if plugin["migrationBlock"].get("apps"):
                details["apps"] = plugin["migrationBlock"]["apps"]
            if plugin["migrationBlock"].get("error"):
                details["error"] = plugin["migrationBlock"]["error"]
            items.append(create_migration_item({
                "id": f"plugin:{sanitize_name(plugin['name']) or sanitize_name(Path(plugin['source']).name)}:{manual_index}",
                "kind": "manual",
                "action": "manual",
                "source": plugin["source"],
                "status": "skipped",
                "reason": plugin["migrationBlock"]["code"],
                "message": plugin.get("message") or f"Codex native plugin \"{plugin['name']}\" was found but not activated automatically.",
                "details": details,
            }))
            continue
        items.append(create_migration_manual_item({
            "id": f"plugin:{sanitize_name(plugin['name']) or sanitize_name(Path(plugin['source']).name)}:{manual_index}",
            "source": plugin["source"],
            "message": plugin.get("message") or f"Codex native plugin \"{plugin['name']}\" was found but not activated automatically.",
            "recommendation": "Review the plugin bundle first, then install trusted compatible plugins with openclaw plugins install <path>.",
        }))
    return items


def _should_verify_plugin_apps(ctx: dict) -> bool:
    return (ctx.get("providerOptions") or {}).get("verifyPluginApps") is True


def read_codex_plugin_migration_config_entry(item: dict, enabled: bool):
    details = item.get("details") or {}
    config_key = details.get("configKey")
    marketplace_name = details.get("marketplaceName")
    plugin_name = details.get("pluginName")
    if item.get("kind") != "plugin" or item.get("action") != "install" or not isinstance(config_key, str) or marketplace_name != CODEX_PLUGINS_MARKETPLACE_NAME or not isinstance(plugin_name, str):
        return None
    entry = {"configKey": config_key, "pluginName": plugin_name, "enabled": enabled}
    allow_destructive_actions = details.get("allowDestructiveActions")
    if allow_destructive_actions == "auto":
        entry["allowDestructiveActions"] = "auto"
    return entry


def _read_existing_allow_destructive_actions(config):
    value = read_migration_config_path(config, [*CODEX_PLUGIN_NATIVE_CONFIG_PATH, "allow_destructive_actions"])
    return _normalize_existing_allow_destructive_actions(value)


def _normalize_existing_allow_destructive_actions(value):
    if value == "auto" or value == "on-request":
        return "auto"
    return as_boolean(value)


def _read_existing_plugin_policy_repairs(config) -> dict:
    if config is None:
        return {}
    repairs = {}
    for config_key, entry in _read_existing_codex_plugin_entries(config).items():
        plugin_entry = entry if isinstance(entry, dict) else None
        if plugin_entry and plugin_entry.get("allow_destructive_actions") == "on-request":
            repairs[config_key] = {**plugin_entry, "allow_destructive_actions": "auto"}
    return repairs


def build_codex_plugins_config_value(entries, params: dict = None) -> dict:
    params = params or {}
    config = params.get("config")
    plugins = {**_read_existing_plugin_policy_repairs(config)}
    for entry in sorted(entries, key=lambda e: e["configKey"]):
        plugin_entry = {"enabled": entry["enabled"], "marketplaceName": CODEX_PLUGINS_MARKETPLACE_NAME, "pluginName": entry["pluginName"]}
        if entry.get("allowDestructiveActions"):
            plugin_entry["allow_destructive_actions"] = entry["allowDestructiveActions"]
        plugins[entry["configKey"]] = plugin_entry
    codex_plugins = {
        "enabled": True,
        "allow_destructive_actions": True if config is None else (_read_existing_allow_destructive_actions(config) or True),
        "plugins": plugins,
    }
    return {"enabled": True, "config": {"codexPlugins": codex_plugins}}


def has_codex_plugin_config_conflict(config, value: dict) -> bool:
    enabled = read_migration_config_path(config, CODEX_PLUGIN_ENABLED_PATH)
    if enabled is not None and enabled is not True:
        return True
    native_config = (value.get("config") or {}).get("codexPlugins") if isinstance(value.get("config"), dict) else None
    if not isinstance(native_config, dict):
        return has_migration_config_patch_conflict(config, CODEX_PLUGIN_NATIVE_CONFIG_PATH, native_config)
    existing_native_config = read_migration_config_path(config, CODEX_PLUGIN_NATIVE_CONFIG_PATH)
    if existing_native_config is None:
        return False
    if not isinstance(existing_native_config, dict):
        return True
    if existing_native_config.get("enabled") is not None and existing_native_config["enabled"] is not True:
        return True
    allow_destructive_actions = native_config.get("allow_destructive_actions")
    existing_allow_destructive_actions = _normalize_existing_allow_destructive_actions(existing_native_config.get("allow_destructive_actions"))
    if existing_native_config.get("allow_destructive_actions") is not None and existing_allow_destructive_actions != allow_destructive_actions:
        return True
    plugins = native_config.get("plugins")
    if not isinstance(plugins, dict):
        return False
    return any(
        (existing_native_config.get(config_key) is not None if not isinstance(plugin, dict) else _has_existing_codex_plugin_entry(_read_existing_codex_plugin_entries(config), config_key, plugin.get("pluginName") if isinstance(plugin.get("pluginName"), str) else config_key, plugin))
        for config_key, plugin in plugins.items()
    )


def _build_plugin_config_item(ctx: dict, plugin_items):
    entries = [read_codex_plugin_migration_config_entry(item, True) for item in plugin_items if item.get("status") == "planned"]
    entries = [e for e in entries if e is not None]
    if not entries:
        return None
    value = build_codex_plugins_config_value(entries, {"config": ctx["config"]})
    conflict = not ctx.get("overwrite") and has_codex_plugin_config_conflict(ctx["config"], value)
    return create_migration_item({
        "id": CODEX_PLUGIN_CONFIG_ITEM_ID,
        "kind": "config",
        "action": "merge",
        "target": "plugins.entries.codex.config.codexPlugins",
        "status": "conflict" if conflict else "planned",
        "reason": MIGRATION_REASON_TARGET_EXISTS if conflict else None,
        "message": "Enable OpenClaw's Codex plugin integration and record migrated source-installed curated plugins.",
        "details": {"path": [*CODEX_PLUGIN_CONFIG_PATH], "value": value},
    })


async def build_codex_migration_plan(ctx: dict) -> dict:
    targets = resolve_codex_migration_targets(ctx)
    source = await discover_codex_source({"input": ctx["source"], "evaluatePluginMigrationEligibility": True, "verifyPluginApps": _should_verify_plugin_apps(ctx)})
    if not has_codex_source(source):
        raise Error(f"Codex state was not found at {source['root']}. Pass --from <path> if it lives elsewhere.")
    items = []
    items.extend(await build_codex_auth_items({"ctx": ctx, "source": source, "targets": targets}))
    items.extend(await _build_skill_items({"skills": source["skills"], "workspaceDir": targets["workspaceDir"], "overwrite": ctx.get("overwrite")}))
    plugin_items = _build_plugin_items(ctx, source["plugins"])
    items.extend(plugin_items)
    plugin_config_item = _build_plugin_config_item(ctx, plugin_items)
    if plugin_config_item:
        items.append(plugin_config_item)
    for archive_path in source["archivePaths"]:
        items.append(create_migration_item({
            "id": archive_path["id"],
            "kind": "archive",
            "action": "archive",
            "source": archive_path["path"],
            "message": archive_path.get("message") or "Archived in the migration report for manual review; not imported into live config.",
            "details": {"archiveRelativePath": archive_path["relativePath"]},
        }))
    warnings = []
    if not ctx.get("includeSecrets") and any(item.get("kind") == "auth" for item in items):
        warnings.append("Auth credentials were detected but skipped. Re-run interactively or pass --include-secrets to import supported credentials.")
    if any(item.get("status") == "conflict" for item in items):
        warnings.append("Conflicts were found. Re-run with --overwrite to replace conflicting migration targets after item-level backups.")
    if source.get("pluginDiscoveryError"):
        warnings.append(f"Codex app-server plugin inventory discovery failed: {source['pluginDiscoveryError']}. Cached plugin bundles, if any, are advisory only.")
    if any((p.get("migrationBlock") or {}).get("code") == "codex_subscription_required" for p in source["plugins"]):
        warnings.append(codex_plugin_migration_subscription_warning())
    return {
        "providerId": "codex",
        "source": source["root"],
        "target": targets["workspaceDir"],
        "summary": summarize_migration_items(items),
        "items": items,
        "warnings": warnings,
        "nextSteps": [
            "Run openclaw doctor after applying the migration.",
            "Review skipped or auth-required Codex plugin/config/hook items before exposing them in OpenClaw sessions.",
        ],
        "metadata": {
            "agentDir": targets["agentDir"],
            "codexHome": source["codexHome"],
            "codexSkillsDir": source.get("codexSkillsDir"),
            "personalAgentsSkillsDir": source.get("personalAgentsSkillsDir"),
        },
    }
