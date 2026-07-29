import asyncio
import os
import time

from openclaw.plugin_sdk.migration import (
    apply_migration_manual_item,
    mark_migration_item_conflict,
    mark_migration_item_error,
    mark_migration_item_skipped,
    MIGRATION_REASON_TARGET_EXISTS,
    summarize_migration_items,
    write_migration_config_path,
)
from openclaw.plugin_sdk.migration_runtime import (
    archive_migration_item,
    copy_migration_file_item,
    with_cached_migration_config_runtime,
    write_migration_report,
)
from openclaw.plugin_sdk.number_runtime import parse_strict_non_negative_integer
from openclaw.plugin_sdk.string_coerce_runtime import unique_strings

from ..app_server.app_inventory_cache import default_codex_app_inventory_cache
from ..app_server.auth_bridge import (
    resolve_codex_app_server_auth_account_cache_key,
    resolve_codex_app_server_auth_profile_id_for_agent,
    resolve_codex_app_server_fallback_api_key_cache_key,
)
from ..app_server.config import (
    CODEX_PLUGINS_MARKETPLACE_NAME,
    read_codex_plugin_config,
    resolve_codex_app_server_runtime_options,
)
from ..app_server.plugin_activation import ensure_codex_plugin_activation
from ..app_server.plugin_app_cache_key import build_codex_plugin_app_cache_key
from ..app_server.request import request_codex_app_server_json
from ..app_server.shared_client import (
    clear_shared_codex_app_server_client_if_current_and_wait,
    get_leased_shared_codex_app_server_client,
    release_leased_shared_codex_app_server_client,
)
from .auth import apply_codex_auth_item, build_codex_auth_config_patch_items
from .plan import (
    build_codex_migration_plan,
    build_codex_plugins_config_value,
    CODEX_PLUGIN_CONFIG_ITEM_ID,
    CODEX_PLUGIN_CONFIG_PATH,
    has_codex_plugin_config_conflict,
    read_codex_plugin_migration_config_entry,
)
from .targets import resolve_codex_migration_targets

CODEX_PLUGIN_AUTH_REQUIRED_REASON = "auth_required"
CODEX_PLUGIN_NOT_SELECTED_REASON = "not selected for migration"
CODEX_CONFIG_PATCH_MODE_RETURN = "return"
CODEX_PLUGIN_LOAD_WARNING = "Some Codex plugins could not be migrated. Run `openclaw migrate codex` after onboarding."
TARGET_CODEX_MARKETPLACE_DISCOVERY_POLL_MS = 250
TARGET_CODEX_MARKETPLACE_DISCOVERY_TIMEOUT_MS = 30_000
TARGET_CODEX_MARKETPLACE_DISCOVERY_TIMEOUT_ENV = "OPENCLAW_CODEX_MIGRATION_PLUGIN_LIST_TIMEOUT_MS"


class CodexPluginConfigConflictError(Exception):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def _should_return_codex_plugin_config_patch(ctx: dict) -> bool:
    return (ctx.get("providerOptions") or {}).get("configPatchMode") == CODEX_CONFIG_PATCH_MODE_RETURN


def prepare_target_codex_app_server(ctx: dict) -> dict:
    app_server = _resolve_target_codex_app_server(ctx)
    targets = resolve_codex_migration_targets(ctx)
    warmed_client = None

    async def ready():
        nonlocal warmed_client
        try:
            warmed_client = await get_leased_shared_codex_app_server_client({
                "startOptions": app_server["start"],
                "timeoutMs": 60_000,
                "agentDir": targets["agentDir"],
                "config": ctx["config"],
            })
        except Exception:
            warmed_client = None

    asyncio.ensure_future(ready())

    async def dispose():
        await ready()
        if warmed_client:
            release_leased_shared_codex_app_server_client(warmed_client)
        await clear_shared_codex_app_server_client_if_current_and_wait(warmed_client, {
            "exitTimeoutMs": 2_000,
            "forceKillDelayMs": 250,
        })

    return {"dispose": dispose}


async def apply_codex_migration_plan(params: dict) -> dict:
    ctx = params["ctx"]
    plan = params.get("plan") or await build_codex_migration_plan(ctx)
    report_dir = ctx.get("reportDir") or os.path.join(ctx["stateDir"], "migration", "codex")
    items = []
    targets = resolve_codex_migration_targets(ctx)
    metadata = plan.get("metadata") or {}
    codex_home = metadata.get("codexHome") if isinstance(metadata.get("codexHome"), str) and metadata.get("codexHome", "").strip() else plan.get("source")
    auth_source = {
        "root": plan.get("source"),
        "confidence": "high",
        "codexHome": codex_home,
        "authPath": os.path.join(codex_home, "auth.json"),
        "modelsCachePath": os.path.join(codex_home, "models_cache.json"),
        "skills": [],
        "plugins": [],
        "archivePaths": [],
    }
    runtime = with_cached_migration_config_runtime(ctx.get("runtime") or params.get("runtime"), ctx["config"])
    apply_ctx = {**ctx, "runtime": runtime}
    for item in plan.get("items", []):
        if item.get("status") != "planned":
            items.append(item)
            continue
        if item.get("id") == CODEX_PLUGIN_CONFIG_ITEM_ID:
            items.append(await _apply_codex_plugin_config_item(apply_ctx, item, items))
        elif item.get("kind") == "auth":
            auth_item = await apply_codex_auth_item({
                "ctx": apply_ctx,
                "item": item,
                "source": auth_source,
                "targets": targets,
            })
            items.append(auth_item)
            items.extend(await build_codex_auth_config_patch_items({
                "ctx": apply_ctx,
                "item": auth_item,
                "source": auth_source,
            }))
        elif item.get("kind") == "plugin" and item.get("action") == "install":
            items.append(await _apply_codex_plugin_install_item(apply_ctx, item))
        elif item.get("kind") == "manual":
            items.append(apply_migration_manual_item(item))
        elif item.get("action") == "archive":
            items.append(await archive_migration_item(item, report_dir))
        else:
            items.append(await copy_migration_file_item(item, report_dir, {"overwrite": ctx.get("overwrite")}))
    result = {
        **plan,
        "items": items,
        "summary": summarize_migration_items(items),
        "backupPath": ctx.get("backupPath"),
        "reportDir": report_dir,
    }
    if any(_is_codex_plugin_load_warning_item(item) for item in items):
        result["warnings"] = unique_strings([*(result.get("warnings") or []), CODEX_PLUGIN_LOAD_WARNING])
        result["nextSteps"] = unique_strings([CODEX_PLUGIN_LOAD_WARNING, *(result.get("nextSteps") or [])])
    await write_migration_report(result, {"title": "Codex Migration Report"})
    return result


async def _apply_codex_plugin_install_item(ctx: dict, item: dict) -> dict:
    policy = _read_codex_plugin_policy(item)
    if not policy:
        return {
            **mark_migration_item_error(item, "invalid Codex plugin migration item"),
            "details": {**(item.get("details") or {}), "code": "invalid_plugin_item"},
        }
    try:
        app_cache_key = await _build_target_codex_plugin_app_cache_key(ctx)
        app_server = _resolve_target_codex_app_server(ctx)
        targets = resolve_codex_migration_targets(ctx)

        async def request(method, request_params):
            return await _request_target_codex_app_server_json({
                "method": method,
                "requestParams": request_params,
                "timeoutMs": 60_000,
                "startOptions": app_server["start"],
                "agentDir": targets["agentDir"],
                "config": ctx["config"],
                "isolated": False,
            })

        activation_result = await ensure_codex_plugin_activation({
            "identity": policy,
            "installEvenIfActive": True,
            "request": request,
            "appCache": default_codex_app_inventory_cache,
            "appCacheKey": app_cache_key,
        })
        base_details = {
            **(item.get("details") or {}),
            "code": activation_result.get("reason"),
            "activationReason": activation_result.get("reason"),
            **_codex_plugin_activation_report_state(activation_result),
            "installAttempted": activation_result.get("installAttempted"),
            "diagnostics": [d.get("message") for d in activation_result.get("diagnostics", [])],
        }
        if activation_result.get("ok"):
            result = {**item, "status": "migrated", "details": base_details}
            if activation_result.get("reason") == "already_active":
                result["reason"] = "already active"
            return result
        if activation_result.get("reason") == CODEX_PLUGIN_AUTH_REQUIRED_REASON:
            install_response = activation_result.get("installResponse") or {}
            return {
                **item,
                "status": "skipped",
                "reason": CODEX_PLUGIN_AUTH_REQUIRED_REASON,
                "details": {
                    **base_details,
                    "appsNeedingAuth": _sanitize_apps_needing_auth(install_response.get("appsNeedingAuth") or []),
                },
            }
        if activation_result.get("reason") in ("plugin_missing", "marketplace_missing"):
            return {
                **item,
                "status": "warning",
                "reason": activation_result["reason"],
                "message": f"Codex plugin \"{policy['pluginName']}\" could not be migrated automatically",
                "details": {**base_details, "warningReason": CODEX_PLUGIN_LOAD_WARNING},
            }
        return {**item, "status": "error", "reason": activation_result.get("reason"), "details": base_details}
    except Exception as error:
        if _is_codex_plugin_inventory_load_error(error):
            return {
                **item,
                "status": "warning",
                "reason": "plugin_inventory_unavailable",
                "message": f"Codex plugin \"{policy['pluginName']}\" could not be migrated automatically",
                "details": {
                    **(item.get("details") or {}),
                    "code": "plugin_inventory_unavailable",
                    "warningReason": CODEX_PLUGIN_LOAD_WARNING,
                    "diagnostic": _format_codex_migration_error(error),
                },
            }
        return {
            **item,
            "status": "error",
            "reason": _format_codex_migration_error(error),
            "details": {**(item.get("details") or {}), "code": "plugin_install_failed"},
        }


def _is_codex_plugin_inventory_load_error(error) -> bool:
    message = _format_codex_migration_error(error)
    return "codex app-server plugin/list timed out" in message


def _format_codex_migration_error(error) -> str:
    return str(error.args[0]) if isinstance(error, Exception) and error.args else str(error)


def _resolve_target_codex_app_server(ctx: dict):
    return resolve_codex_app_server_runtime_options({
        "pluginConfig": read_codex_plugin_config(ctx["config"]),
    })


async def _request_target_codex_app_server_json(params: dict):
    if params["method"] != "plugin/list":
        return await request_codex_app_server_json(params)
    deadline = time.time() * 1000 + params["timeoutMs"]
    discovery_timeout_ms = _target_codex_marketplace_discovery_timeout_ms()
    discovery_deadline = min(deadline, time.time() * 1000 + discovery_timeout_ms)
    last_response = None
    while True:
        remaining_ms = max(1, int(discovery_deadline - time.time() * 1000))
        last_response = await request_codex_app_server_json({**params, "timeoutMs": remaining_ms})
        if _has_openai_curated_marketplace(last_response):
            return last_response
        if time.time() * 1000 >= discovery_deadline:
            return last_response
        wait_ms = min(TARGET_CODEX_MARKETPLACE_DISCOVERY_POLL_MS, discovery_deadline - time.time() * 1000)
        await asyncio.sleep(wait_ms / 1000)


def _has_openai_curated_marketplace(response) -> bool:
    if not isinstance(response, dict) or "marketplaces" not in response:
        return False
    marketplaces = response.get("marketplaces")
    return (
        isinstance(marketplaces, list)
        and any(
            isinstance(marketplace, dict) and marketplace.get("name") == CODEX_PLUGINS_MARKETPLACE_NAME
            for marketplace in marketplaces
        )
    )


def _target_codex_marketplace_discovery_timeout_ms() -> int:
    configured = parse_strict_non_negative_integer(os.environ.get(TARGET_CODEX_MARKETPLACE_DISCOVERY_TIMEOUT_ENV))
    if configured is not None:
        return configured
    return TARGET_CODEX_MARKETPLACE_DISCOVERY_TIMEOUT_MS


def _is_codex_plugin_load_warning_item(item: dict) -> bool:
    return (
        item.get("kind") == "plugin"
        and item.get("action") == "install"
        and item.get("status") == "warning"
        and (item.get("details") or {}).get("warningReason") == CODEX_PLUGIN_LOAD_WARNING
    )


async def _build_target_codex_plugin_app_cache_key(ctx: dict) -> str:
    targets = resolve_codex_migration_targets(ctx)
    app_server = _resolve_target_codex_app_server(ctx)
    auth_profile_id = resolve_codex_app_server_auth_profile_id_for_agent({
        "agentDir": targets["agentDir"],
        "config": ctx["config"],
    })
    account_id = await resolve_codex_app_server_auth_account_cache_key({
        "authProfileId": auth_profile_id,
        "agentDir": targets["agentDir"],
        "config": ctx["config"],
    })
    env_api_key_fingerprint = (
        None
        if auth_profile_id
        else resolve_codex_app_server_fallback_api_key_cache_key({"startOptions": app_server["start"]})
    )
    return build_codex_plugin_app_cache_key({
        "appServer": app_server,
        "agentDir": targets["agentDir"],
        "authProfileId": auth_profile_id,
        "accountId": account_id,
        "envApiKeyFingerprint": env_api_key_fingerprint,
    })


async def _apply_codex_plugin_config_item(ctx: dict, item: dict, applied_items: list) -> dict:
    entries = []
    for applied in applied_items:
        entry = _read_applied_plugin_config_entry(applied)
        if entry is not None:
            entries.append(entry)
    if not entries:
        return mark_migration_item_skipped(item, "no selected Codex plugins")
    return_patch = _should_return_codex_plugin_config_patch(ctx)
    runtime = ctx.get("runtime") or {}
    config_api = runtime.get("config") or {}
    current_config = ctx["config"] if return_patch else config_api.get("current", lambda: None)()
    if not current_config:
        return mark_migration_item_error(item, "config runtime unavailable")
    value = build_codex_plugins_config_value(entries, {"config": current_config})
    if not ctx.get("overwrite") and has_codex_plugin_config_conflict(current_config, value):
        return mark_migration_item_conflict(item, MIGRATION_REASON_TARGET_EXISTS)
    migrated_item = {
        **item,
        "status": "migrated",
        "details": {**(item.get("details") or {}), "path": [*CODEX_PLUGIN_CONFIG_PATH], "value": value},
    }
    if return_patch:
        return migrated_item
    if not config_api.get("mutateConfigFile"):
        return mark_migration_item_error(item, "config runtime unavailable")
    try:
        await config_api["mutateConfigFile"]({
            "base": "runtime",
            "afterWrite": {"mode": "auto"},
            "mutate": lambda draft: _mutate_plugin_config(draft, ctx, value),
        })
        return migrated_item
    except CodexPluginConfigConflictError as error:
        return mark_migration_item_conflict(item, error.reason)
    except Exception as error:
        return mark_migration_item_error(item, _format_codex_migration_error(error))


def _mutate_plugin_config(draft: dict, ctx: dict, value: dict) -> None:
    if not ctx.get("overwrite") and has_codex_plugin_config_conflict(draft, value):
        raise CodexPluginConfigConflictError(MIGRATION_REASON_TARGET_EXISTS)
    write_migration_config_path(draft, CODEX_PLUGIN_CONFIG_PATH, value)


def _read_applied_plugin_config_entry(item: dict):
    if item.get("status") == "migrated":
        return read_codex_plugin_migration_config_entry(item, True)
    if item.get("status") == "skipped" and item.get("reason") != CODEX_PLUGIN_NOT_SELECTED_REASON and item.get("reason") == CODEX_PLUGIN_AUTH_REQUIRED_REASON:
        return read_codex_plugin_migration_config_entry(item, False)
    return None


def _read_codex_plugin_policy(item: dict):
    details = item.get("details") or {}
    config_key = details.get("configKey")
    marketplace_name = details.get("marketplaceName")
    plugin_name = details.get("pluginName")
    if not isinstance(config_key, str) or marketplace_name != CODEX_PLUGINS_MARKETPLACE_NAME or not isinstance(plugin_name, str):
        return None
    return {
        "configKey": config_key,
        "marketplaceName": CODEX_PLUGINS_MARKETPLACE_NAME,
        "pluginName": plugin_name,
        "enabled": True,
        "allowDestructiveActions": True,
        "destructiveApprovalMode": "allow",
    }


def _codex_plugin_activation_report_state(result: dict) -> dict:
    reason = result.get("reason")
    if reason in ("already_active", "installed"):
        return {"installed": True, "enabled": True}
    if reason == "auth_required":
        return {"installed": True, "enabled": False}
    if reason in ("disabled", "marketplace_missing", "plugin_missing"):
        return {"installed": False, "enabled": False}
    if reason == "refresh_failed":
        return {"installed": True, "enabled": False}
    return {}


def _sanitize_apps_needing_auth(apps: list) -> list:
    return [{"id": app.get("id"), "name": app.get("name"), "needsAuth": app.get("needsAuth")} for app in apps]
