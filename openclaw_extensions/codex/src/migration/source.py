import re
from pathlib import Path

from ..app_server.app_inventory_cache import default_codex_app_inventory_cache
from ..app_server.config import CODEX_PLUGINS_MARKETPLACE_NAME
from ..app_server.plugin_app_cache_key import build_codex_plugin_app_cache_key
from ..app_server.plugin_inventory import plugin_read_params
from ..app_server.protocol import CodexGetAccountResponse
from ..app_server.request import request_codex_app_server_json
from .helpers import exists, is_directory, read_json_object, resolve_home_path, resolve_user_home_dir

SKILL_FILENAME = "SKILL.md"
MAX_SCAN_DEPTH = 6
MAX_DISCOVERED_DIRS = 2000


def _default_codex_home() -> str:
    return resolve_home_path(os.environ.get("CODEX_HOME", "").strip() or "~/.codex")


import os


def _personal_agents_skills_dir() -> str:
    return str(Path(resolve_user_home_dir(), ".agents", "skills"))


async def _safe_read_dir(dir_path: str):
    try:
        return list(Path(dir_path).iterdir())
    except OSError:
        return []


async def _discover_skill_dirs(params: dict):
    root = params.get("root")
    if not root or not await is_directory(root):
        return []
    discovered = []

    async def visit(dir_path: str, depth: int):
        if len(discovered) >= MAX_DISCOVERED_DIRS or depth > MAX_SCAN_DEPTH:
            return
        name = Path(dir_path).name
        if params.get("excludeSystem") and depth == 1 and name == ".system":
            return
        skill_path = str(Path(dir_path, SKILL_FILENAME))
        if await exists(skill_path):
            discovered.append({"name": name, "source": dir_path, "sourceLabel": params["sourceLabel"]})
            return
        for entry in await _safe_read_dir(dir_path):
            if entry.is_dir():
                await visit(str(entry), depth + 1)

    await visit(root, 0)
    return discovered


async def _discover_plugin_dirs(codex_home: str):
    root = str(Path(codex_home, "plugins", "cache"))
    if not await is_directory(root):
        return []
    discovered: dict = {}

    async def visit(dir_path: str, depth: int):
        if len(discovered) >= MAX_DISCOVERED_DIRS or depth > MAX_SCAN_DEPTH:
            return
        manifest_path = str(Path(dir_path, ".codex-plugin", "plugin.json"))
        if await exists(manifest_path):
            manifest = await read_json_object(manifest_path)
            manifest_name = manifest.get("name", "").strip() if isinstance(manifest.get("name"), str) else ""
            name = manifest_name or Path(dir_path).name
            discovered[dir_path] = {
                "name": name,
                "source": dir_path,
                "manifestPath": manifest_path,
                "sourceKind": "cache",
                "migratable": False,
                "message": "Cached Codex plugin bundle found. Review manually unless the plugin is also installed in the source Codex app-server inventory",
            }
            return
        for entry in await _safe_read_dir(dir_path):
            if entry.is_dir():
                await visit(str(entry), depth + 1)

    await visit(root, 0)
    return sorted(discovered.values(), key=lambda p: p["source"])


async def _discover_installed_curated_plugins(codex_home: str, options: dict = None):
    options = options or {}
    start_options = _source_codex_app_server_start_options(codex_home)
    request_options = {"startOptions": start_options}
    try:
        response = await _request_source_codex_app_server_json(request_options, {
            "method": "plugin/list",
            "requestParams": {"cwds": []},
        })
        marketplace = next((entry for entry in response.get("marketplaces", []) if entry.get("name") == CODEX_PLUGINS_MARKETPLACE_NAME), None)
        if not marketplace:
            return {"plugins": [], "error": f"Codex marketplace {CODEX_PLUGINS_MARKETPLACE_NAME} was not found in source plugin inventory."}
        plugins = [_build_installed_plugin_source(plugin) for plugin in marketplace["plugins"] if plugin.get("installed")]
        plugins = [p for p in plugins if p is not None]
        if options.get("evaluatePluginMigrationEligibility") is True:
            plugins = await _with_plugin_migration_eligibility({
                "plugins": plugins,
                "marketplace": _marketplace_ref(marketplace),
                "requestOptions": request_options,
                "verifyPluginApps": options.get("verifyPluginApps") is True,
            })
        plugins.sort(key=lambda p: (p.get("pluginName") or p["name"]))
        return {"plugins": plugins}
    except Exception as error:
        return {"plugins": [], "error": str(error)}


def _source_codex_app_server_start_options(codex_home: str) -> dict:
    return {
        "transport": "stdio",
        "command": "codex",
        "commandSource": "managed",
        "args": ["app-server", "--listen", "stdio://"],
        "headers": {},
        "env": {"CODEX_HOME": codex_home, "HOME": str(Path(codex_home).parent)},
    }


async def _request_source_codex_app_server_json(options: dict, params: dict):
    return await request_codex_app_server_json({
        "method": params["method"],
        "requestParams": params.get("requestParams"),
        "timeoutMs": 60_000,
        "startOptions": options["startOptions"],
        "authProfileId": None,
        "isolated": True,
    })


def _build_installed_plugin_source(plugin: dict):
    plugin_name = _plugin_name_from_summary(plugin)
    if not plugin_name:
        return None
    return {
        "name": plugin["name"],
        "pluginName": plugin_name,
        "marketplaceName": CODEX_PLUGINS_MARKETPLACE_NAME,
        "source": f"{CODEX_PLUGINS_MARKETPLACE_NAME}/{plugin_name}",
        "sourceKind": "app-server",
        "migratable": True,
        "installed": plugin.get("installed"),
        "enabled": plugin.get("enabled"),
    }


def _marketplace_ref(marketplace: dict) -> dict:
    ref = {"name": CODEX_PLUGINS_MARKETPLACE_NAME}
    if marketplace.get("path"):
        ref["path"] = marketplace["path"]
    else:
        ref["remoteMarketplaceName"] = marketplace["name"]
    return ref


async def _with_plugin_migration_eligibility(params: dict):
    pending = []
    evaluated = []
    for plugin in params["plugins"]:
        if plugin.get("enabled") is not True:
            evaluated.append({**plugin, "migratable": False, "migrationBlock": {"code": "plugin_disabled"}, "message": f"Codex plugin \"{plugin.get('pluginName') or plugin['name']}\" is installed in Codex but disabled; enable it in Codex before migrating it to OpenClaw."})
            continue
        detail = await _read_plugin_detail(params["requestOptions"], params["marketplace"], plugin)
        if not detail["ok"]:
            evaluated.append({**plugin, "migratable": False, "migrationBlock": {"code": "plugin_read_unavailable", "error": detail["error"]}, "message": f"Codex plugin \"{plugin.get('pluginName') or plugin['name']}\" detail could not be read: {detail['error']}"})
            continue
        if not detail["detail"].get("apps"):
            evaluated.append({**plugin, "migratable": True})
            continue
        apps = sorted((_source_plugin_app_fact(app) for app in detail["detail"]["apps"]), key=lambda a: a["id"])
        pending.append({"plugin": plugin, "apps": apps})
    if not pending:
        return evaluated
    source_account = None
    try:
        source_account = await _read_source_codex_account(params["requestOptions"])
    except Exception as error:
        if not params["verifyPluginApps"]:
            message = str(error)
            for item in pending:
                evaluated.append({**item["plugin"], "migratable": False, "migrationBlock": {"code": "codex_account_unavailable", "apps": item["apps"], "error": message}, "message": f"Codex plugin \"{item['plugin'].get('pluginName') or item['plugin']['name']}\" owns apps, but the source Codex app-server account could not be read: {message}"})
            return evaluated
    if source_account and source_account != "chatgpt":
        for item in pending:
            evaluated.append({**item["plugin"], "migratable": False, "migrationBlock": {"code": "codex_subscription_required", "apps": item["apps"]}, "message": _codex_subscription_required_message(item["plugin"])})
        return evaluated
    if not params["verifyPluginApps"]:
        for item in pending:
            evaluated.append({**item["plugin"], "apps": item["apps"], "migratable": True})
        return evaluated
    try:
        snapshot = await _refresh_source_app_inventory(params["requestOptions"])
    except Exception as error:
        message = str(error)
        for item in pending:
            evaluated.append({**item["plugin"], "migratable": False, "migrationBlock": {"code": "app_inventory_unavailable", "apps": item["apps"], "error": message}, "message": f"Codex plugin \"{item['plugin'].get('pluginName') or item['plugin']['name']}\" owns apps, but source app inventory could not be read: {message}"})
        return evaluated
    if not snapshot:
        return evaluated
    app_info_by_id = {app["id"]: app for app in snapshot["apps"]}
    for item in pending:
        apps = sorted((_source_plugin_app_fact_with_inventory(app, app_info_by_id.get(app["id"])) for app in item["apps"]), key=lambda a: a["id"])
        block_code = _migration_block_code_for_apps(apps)
        if not block_code:
            evaluated.append({**item["plugin"], "apps": apps, "migratable": True})
            continue
        evaluated.append({**item["plugin"], "migratable": False, "migrationBlock": {"code": block_code, "apps": apps}, "message": _app_inventory_block_message(item["plugin"], apps, block_code)})
    return evaluated


async def _read_source_codex_account(options: dict) -> str:
    response = await _request_source_codex_app_server_json(options, {"method": "account/read", "requestParams": {"refreshToken": False}})
    account = response.get("account")
    if not account or not isinstance(account, dict) or isinstance(account, list):
        return "missing"
    return "chatgpt" if account.get("type") == "chatgpt" else "non_chatgpt"


async def _read_plugin_detail(options: dict, marketplace: dict, plugin: dict) -> dict:
    try:
        response = await _request_source_codex_app_server_json(options, {"method": "plugin/read", "requestParams": plugin_read_params(marketplace, plugin.get("pluginName") or plugin["name"])})
        return {"ok": True, "detail": response["plugin"]}
    except Exception as error:
        return {"ok": False, "error": str(error)}


async def _refresh_source_app_inventory(options: dict):
    key = build_codex_plugin_app_cache_key({"appServer": {"start": options["startOptions"]}})

    async def request(method, request_params):
        return await _request_source_codex_app_server_json(options, {"method": method, "requestParams": request_params})

    return await default_codex_app_inventory_cache.refresh_now({"key": key, "request": request, "forceRefetch": True})


def _source_plugin_app_fact(app: dict) -> dict:
    return {"id": app["id"], "name": app["name"], "needsAuth": app.get("needsAuth")}


def _source_plugin_app_fact_with_inventory(app: dict, info) -> dict:
    if not info:
        return app
    return {**app, "isAccessible": info.get("isAccessible"), "isEnabled": info.get("isEnabled")}


def _migration_block_code_for_apps(apps):
    if any(app.get("isAccessible") is False for app in apps):
        return "app_inaccessible"
    if any(app.get("isEnabled") is False for app in apps):
        return "app_disabled"
    if any(app.get("isAccessible") is None or app.get("isEnabled") is None for app in apps):
        return "app_missing"
    return None


def _app_inventory_block_message(plugin: dict, apps, code: str) -> str:
    status = "inaccessible" if code == "app_inaccessible" else ("disabled" if code == "app_disabled" else "missing")
    blocking = next((app for app in apps if (code == "app_inaccessible" and app.get("isAccessible") is False) or (code == "app_disabled" and app.get("isEnabled") is False) or (code == "app_missing" and (app.get("isAccessible") is None or app.get("isEnabled") is None))), apps[0] if apps else None)
    app_label = f" app \"{blocking['name']}\"" if blocking else " an owned app"
    return f"Codex plugin \"{plugin.get('pluginName') or plugin['name']}\" owns{app_label} but the source app inventory reports it is {status}; authenticate or enable the app in Codex before migrating it to OpenClaw."


def codex_plugin_migration_subscription_warning() -> str:
    return "Codex app-backed plugin migration requires the Codex app-server source account to be logged in with a ChatGPT subscription account. Log in to the Codex app with subscription auth; OpenClaw auth or API-key auth does not satisfy Codex app connector access."


def _codex_subscription_required_message(plugin: dict) -> str:
    return f"Codex plugin \"{plugin.get('pluginName') or plugin['name']}\" owns apps, but {codex_plugin_migration_subscription_warning()}"


def _plugin_name_from_summary(summary: dict):
    candidates = [summary.get("id"), summary.get("name")]
    for candidate in candidates:
        if not candidate:
            continue
        trimmed = candidate.strip()
        if not trimmed:
            continue
        without_marketplace_suffix = trimmed[: -len(f"@{CODEX_PLUGINS_MARKETPLACE_NAME}")] if trimmed.endswith(f"@{CODEX_PLUGINS_MARKETPLACE_NAME}") else trimmed
        path_segment = (without_marketplace_suffix.split("/")[-1] or "").strip()
        normalized = re.sub(r"\s+", "-", path_segment.lower()) if path_segment else None
        if normalized:
            return normalized
    return None


async def discover_codex_source(input_or_options=None) -> dict:
    if isinstance(input_or_options, str) or input_or_options is None:
        options = {"input": input_or_options}
    else:
        options = input_or_options
    codex_home = resolve_home_path((options.get("input") or "").strip() or _default_codex_home())
    codex_skills_dir = str(Path(codex_home, "skills"))
    agents_skills_dir = _personal_agents_skills_dir()
    config_path = str(Path(codex_home, "config.toml"))
    auth_path = str(Path(codex_home, "auth.json"))
    models_cache_path = str(Path(codex_home, "models_cache.json"))
    hooks_path = str(Path(codex_home, "hooks", "hooks.json"))
    codex_skills = await _discover_skill_dirs({"root": codex_skills_dir, "sourceLabel": "Codex skill", "excludeSystem": True})
    personal_agent_skills = await _discover_skill_dirs({"root": agents_skills_dir, "sourceLabel": "personal AgentSkill"})
    source_plugin_discovery = await _discover_installed_curated_plugins(codex_home, options)
    source_plugin_names = {plugin["pluginName"] for plugin in source_plugin_discovery["plugins"] if plugin.get("pluginName")}
    cached_plugins = [plugin for plugin in (await _discover_plugin_dirs(codex_home)) if _sanitize_plugin_name(plugin["name"]) not in source_plugin_names]
    plugins = sorted([*source_plugin_discovery["plugins"], *cached_plugins], key=lambda p: p["source"])
    archive_paths = []
    if await exists(config_path):
        archive_paths.append({"id": "archive:config.toml", "path": config_path, "relativePath": "config.toml", "message": "Codex config is archived for manual review; it is not activated automatically"})
    if await exists(hooks_path):
        archive_paths.append({"id": "archive:hooks/hooks.json", "path": hooks_path, "relativePath": "hooks/hooks.json", "message": "Codex native hooks are archived for manual review because they can execute commands"})
    skills = sorted([*codex_skills, *personal_agent_skills], key=lambda s: s["source"])
    has_auth = await exists(auth_path)
    high = bool(codex_skills or plugins or archive_paths or has_auth)
    medium = len(personal_agent_skills) > 0
    result = {
        "root": codex_home,
        "confidence": "high" if high else ("medium" if medium else "low"),
        "codexHome": codex_home,
        "skills": skills,
        "plugins": plugins,
        "archivePaths": archive_paths,
    }
    if await is_directory(codex_skills_dir):
        result["codexSkillsDir"] = codex_skills_dir
    if await is_directory(agents_skills_dir):
        result["personalAgentsSkillsDir"] = agents_skills_dir
    if await exists(config_path):
        result["configPath"] = config_path
    if has_auth:
        result["authPath"] = auth_path
    if await exists(models_cache_path):
        result["modelsCachePath"] = models_cache_path
    if await exists(hooks_path):
        result["hooksPath"] = hooks_path
    if source_plugin_discovery.get("error"):
        result["pluginDiscoveryError"] = source_plugin_discovery["error"]
    return result


def has_codex_source(source: dict) -> bool:
    return source["confidence"] != "low"


def _sanitize_plugin_name(value: str) -> str:
    return re.sub(r"\s+", "-", value.strip().lower())
