from openclaw.plugin_sdk.agent_runtime import load_auth_profile_store_without_external_profiles
from openclaw.plugin_sdk.migration import (
    create_migration_item,
    mark_migration_item_conflict,
    mark_migration_item_error,
    mark_migration_item_skipped,
)
from openclaw.plugin_sdk.provider_auth import (
    apply_auth_profile_config,
    build_api_key_credential,
    build_openai_codex_credential_extra,
    build_oauth_provider_auth_result,
    read_codex_cli_credentials_cached,
    resolve_openai_codex_auth_identity,
    resolve_openai_codex_import_profile_name,
    update_auth_profile_store_with_lock,
)
from openclaw.plugin_sdk.string_coerce_runtime import is_record, normalize_optional_string as read_string

from .helpers import read_json_object

OPENAI_PROVIDER_ID = "openai"
OPENAI_CODEX_DEFAULT_MODEL = "openai/gpt-5.5"
CODEX_IMPORT_DISPLAY_NAME = "Codex import"
CODEX_REASON_AUTH_NOT_SELECTED = "auth credential migration not selected"
CODEX_REASON_AUTH_PROFILE_EXISTS = "auth profile exists"
CODEX_REASON_AUTH_PROFILE_WRITE_FAILED = "failed to write auth profile"
CODEX_REASON_AUTH_NO_LONGER_PRESENT = "auth credential no longer present"
CODEX_REASON_MISSING_AUTH_METADATA = "missing auth metadata"
CODEX_CONFIG_PATCH_MODE_RETURN = "return"


class CodexAuthConfigConflict(Exception):
    pass


async def _read_model_refs(source: dict) -> list:
    cache = await read_json_object(source.get("modelsCachePath"))
    models = cache.get("models") if isinstance(cache.get("models"), list) else []
    refs = set()
    for model in models:
        if isinstance(model, str):
            slug = model.strip()
        elif is_record(model):
            slug = read_string(model.get("slug")) or read_string(model.get("id")) or read_string(model.get("name"))
        else:
            slug = None
        if not slug:
            continue
        refs.add(f"{OPENAI_PROVIDER_ID}/{slug}")
    refs.add(OPENAI_CODEX_DEFAULT_MODEL)
    return sorted(refs)


def _read_provider_auth_model_configs(result: dict) -> dict:
    config_patch = result.get("configPatch") or {}
    agents = config_patch.get("agents") if is_record(config_patch) else None
    defaults = agents.get("defaults") if is_record(agents) else None
    models = defaults.get("models") if is_record(defaults) else None
    if is_record(models):
        return {**models}
    default_model = read_string(result.get("defaultModel")) or OPENAI_CODEX_DEFAULT_MODEL
    return {default_model: {}}


async def _build_codex_oauth_credential(source: dict):
    credential = read_codex_cli_credentials_cached({
        "codexHome": source["codexHome"],
        "allowKeychainPrompt": False,
        "ttlMs": 0,
    })
    if not credential:
        return None
    identity = resolve_openai_codex_auth_identity({
        "access": credential.get("access"),
        "accountId": credential.get("accountId"),
    })
    model_refs = await _read_model_refs(source)
    config_patch = {
        "agents": {
            "defaults": {
                "models": {model_ref: {} for model_ref in model_refs},
            },
        },
    }
    result = build_oauth_provider_auth_result({
        "providerId": OPENAI_PROVIDER_ID,
        "defaultModel": OPENAI_CODEX_DEFAULT_MODEL,
        "access": credential.get("access"),
        "refresh": credential.get("refresh"),
        "expires": credential.get("expires"),
        "email": identity.get("email"),
        "profileName": resolve_openai_codex_import_profile_name(identity, "codex-import"),
        "displayName": CODEX_IMPORT_DISPLAY_NAME,
        "credentialExtra": build_openai_codex_credential_extra({
            "accountId": identity.get("accountId"),
            "chatgptPlanType": identity.get("chatgptPlanType"),
            "idToken": credential.get("idToken"),
        }),
        "configPatch": config_patch,
    })
    profile = result["profiles"][0] if result.get("profiles") else None
    if not profile:
        return None
    return {
        "kind": "oauth",
        "provider": OPENAI_PROVIDER_ID,
        "profileId": profile["profileId"],
        "result": result,
        "modelConfigs": _read_provider_auth_model_configs(result),
    }


async def _build_codex_api_key_credential(source: dict):
    raw = await read_json_object(source.get("authPath"))
    key = read_string(raw.get("OPENAI_API_KEY"))
    if not key:
        return None
    return {
        "kind": "api_key",
        "provider": OPENAI_PROVIDER_ID,
        "profileId": "openai:codex-import",
        "key": key,
    }


async def _read_codex_auth_credentials(source: dict) -> list:
    oauth = await _build_codex_oauth_credential(source)
    api_key = await _build_codex_api_key_credential(source)
    return [entry for entry in [oauth, api_key] if entry is not None]


def _find_matching_oauth_profile(store: dict, credential: dict):
    profiles = store.get("profiles") or {}
    for profile_id, existing in profiles.items():
        if existing.get("type") != "oauth" or existing.get("provider") != credential.get("provider"):
            continue
        if credential.get("accountId") and existing.get("accountId") == credential.get("accountId"):
            return profile_id
        can_match_by_email = not credential.get("accountId") or not existing.get("accountId")
        if can_match_by_email and credential.get("email") and existing.get("email") == credential.get("email"):
            return profile_id
    return None


def _find_matching_api_key_profile(store: dict, provider: str, key: str):
    profiles = store.get("profiles") or {}
    for profile_id, existing in profiles.items():
        if existing.get("type") == "api_key" and existing.get("provider") == provider and existing.get("key") == key:
            return profile_id
    return None


def _item_profile_target(credential: dict, store: dict) -> dict:
    if credential["kind"] == "oauth":
        profile = credential["result"]["profiles"][0] if credential["result"].get("profiles") else None
        credential_obj = profile.get("credential") if profile else None
        matched = _find_matching_oauth_profile(store, credential_obj) if credential_obj and credential_obj.get("type") == "oauth" else None
        return {"profileId": matched or credential["profileId"], "matchedExisting": matched is not None}
    matched = _find_matching_api_key_profile(store, credential["provider"], credential["key"])
    return {"profileId": matched or credential["profileId"], "matchedExisting": matched is not None}


def _replace_config_draft(draft: dict, next_config: dict) -> None:
    for key in list(draft.keys()):
        del draft[key]
    draft.update(next_config)


def _existing_auth_profile_config_is_compatible(existing: dict, profile: dict) -> bool:
    if existing.get("provider") != profile.get("provider") or existing.get("mode") != profile.get("mode"):
        return False
    if existing.get("email") and profile.get("email") and existing.get("email") != profile.get("email"):
        return False
    return True


def _has_auth_profile_config_conflict(config: dict, profile: dict, overwrite: bool) -> bool:
    if overwrite:
        return False
    auth = config.get("auth") or {}
    profiles = auth.get("profiles") or {}
    existing = profiles.get(profile["profileId"])
    return bool(existing and not _existing_auth_profile_config_is_compatible(existing, profile))


def _has_current_auth_profile_config_conflict(ctx: dict, profile: dict) -> bool:
    config = ctx["config"]
    runtime = ctx.get("runtime") or {}
    config_api = runtime.get("config") or {}
    try:
        current = config_api.get("current", lambda: None)()
        if current is not None:
            config = current
    except Exception:
        pass
    return _has_auth_profile_config_conflict(config, profile, bool(ctx.get("overwrite")))


def _apply_default_model_if_missing(cfg: dict) -> dict:
    agents = cfg.get("agents") or {}
    defaults = agents.get("defaults") or {}
    current_model = defaults.get("model")
    if isinstance(current_model, str):
        primary = current_model
    elif is_record(current_model):
        primary = read_string(current_model.get("primary"))
    else:
        primary = None
    if primary:
        return cfg
    return {
        **cfg,
        "agents": {
            **agents,
            "defaults": {
                **defaults,
                "model": {
                    **(current_model if is_record(current_model) else {}),
                    "primary": OPENAI_CODEX_DEFAULT_MODEL,
                },
            },
        },
    }


def _merge_model_config_entry(existing, patch: dict) -> dict:
    if existing and is_record(existing) and is_record(patch):
        return {**existing, **patch}
    return existing if existing is not None else patch


def _apply_oauth_model_configs_to_config(cfg: dict, credential: dict) -> dict:
    agents = cfg.get("agents") or {}
    defaults = agents.get("defaults") or {}
    existing_models = defaults.get("models") or {}
    if credential["result"].get("replaceDefaultModels"):
        models = {**credential["modelConfigs"]}
    else:
        models = {**existing_models}
    if not credential["result"].get("replaceDefaultModels"):
        for model_ref, model_config in credential["modelConfigs"].items():
            models[model_ref] = _merge_model_config_entry(models.get(model_ref), model_config)
    return {
        **cfg,
        "agents": {
            **agents,
            "defaults": {
                **defaults,
                "models": models,
            },
        },
    }


def _apply_oauth_config_to_config(cfg: dict, credential: dict, profile_id: str) -> dict:
    next_cfg = _apply_oauth_model_configs_to_config(cfg, credential)
    profile = credential["result"]["profiles"][0] if credential["result"].get("profiles") else None
    if profile:
        credential_obj = profile.get("credential") or {}
        auth_profile_kwargs = {
            "profileId": profile_id,
            "provider": credential_obj.get("provider"),
            "mode": "oauth",
            "preferProfileFirst": False,
        }
        if credential_obj.get("email"):
            auth_profile_kwargs["email"] = credential_obj["email"]
        if credential_obj.get("displayName"):
            auth_profile_kwargs["displayName"] = credential_obj["displayName"]
        next_cfg = apply_auth_profile_config(next_cfg, auth_profile_kwargs)
    return _apply_default_model_if_missing(next_cfg)


def _apply_api_key_config_to_config(cfg: dict, credential: dict, profile_id: str) -> dict:
    return apply_auth_profile_config(cfg, {
        "profileId": profile_id,
        "provider": credential["provider"],
        "mode": "api_key",
        "displayName": CODEX_IMPORT_DISPLAY_NAME,
        "preferProfileFirst": False,
    })


def _should_return_auth_config_patch(ctx: dict) -> bool:
    return (ctx.get("providerOptions") or {}).get("configPatchMode") == CODEX_CONFIG_PATCH_MODE_RETURN


def _oauth_auth_profile_config(credential: dict, profile_id: str):
    profile = credential["result"]["profiles"][0] if credential["result"].get("profiles") else None
    if not profile:
        return None
    credential_obj = profile.get("credential") or {}
    if credential_obj.get("type") != "oauth":
        return None
    result = {
        "profileId": profile_id,
        "provider": credential_obj.get("provider"),
        "mode": "oauth",
    }
    if credential_obj.get("email"):
        result["email"] = credential_obj["email"]
    if credential_obj.get("displayName"):
        result["displayName"] = credential_obj["displayName"]
    return result


def _api_key_auth_profile_config(credential: dict, profile_id: str) -> dict:
    return {
        "profileId": profile_id,
        "provider": credential["provider"],
        "mode": "api_key",
        "displayName": CODEX_IMPORT_DISPLAY_NAME,
    }


def _auth_profile_config_for_credential(credential: dict, profile_id: str):
    if credential["kind"] == "oauth":
        return _oauth_auth_profile_config(credential, profile_id)
    return _api_key_auth_profile_config(credential, profile_id)


async def _apply_codex_auth_profile_config(ctx: dict, profile: dict, apply_config) -> str:
    runtime = ctx.get("runtime") or {}
    config_api = runtime.get("config") or {}
    if not config_api.get("current") or not config_api.get("mutateConfigFile"):
        return "unavailable"
    try:
        await config_api["mutateConfigFile"]({
            "base": "runtime",
            "afterWrite": {"mode": "auto"},
            "mutate": lambda draft: _mutate_auth_config(draft, ctx, profile, apply_config),
        })
        return "configured"
    except CodexAuthConfigConflict:
        return "conflict"
    except Exception:
        return "unavailable"


def _mutate_auth_config(draft: dict, ctx: dict, profile: dict, apply_config) -> None:
    if _has_auth_profile_config_conflict(draft, profile, bool(ctx.get("overwrite"))):
        raise CodexAuthConfigConflict()
    next_config = apply_config(draft)
    _replace_config_draft(draft, next_config)


async def _apply_oauth_config(ctx: dict, credential: dict, profile_id: str) -> str:
    profile = _oauth_auth_profile_config(credential, profile_id)
    if not profile:
        return "unavailable"
    return await _apply_codex_auth_profile_config(ctx, profile, lambda config: _apply_oauth_config_to_config(config, credential, profile_id))


async def _apply_api_key_config(ctx: dict, credential: dict, profile_id: str) -> str:
    return await _apply_codex_auth_profile_config(
        ctx,
        _api_key_auth_profile_config(credential, profile_id),
        lambda config: _apply_api_key_config_to_config(config, credential, profile_id),
    )


async def build_codexAuth_items(params: dict) -> list:
    ctx = params["ctx"]
    source = params["source"]
    targets = params["targets"]
    credentials = await _read_codex_auth_credentials(source)
    if not credentials:
        return []
    store = load_auth_profile_store_without_external_profiles(targets["agentDir"])
    skipped = not ctx.get("includeSecrets")
    items = []
    for credential in credentials:
        target = _item_profile_target(credential, store)
        profile_id = target["profileId"]
        matched_existing = target["matchedExisting"]
        profiles = store.get("profiles") or {}
        target_exists = bool(profiles.get(profile_id))
        config_profile = _auth_profile_config_for_credential(credential, profile_id)
        config_conflict = _has_auth_profile_config_conflict(ctx["config"], config_profile, bool(ctx.get("overwrite"))) if config_profile else False
        conflict = ((target_exists and not matched_existing and not ctx.get("overwrite")) or config_conflict) and not skipped
        items.append(create_migration_item({
            "id": f"auth:{credential['provider']}",
            "kind": "auth",
            "action": "skip" if skipped else "create",
            "source": source.get("authPath"),
            "target": f"{targets['agentDir']}/auth-profiles.json#{profile_id}",
            "status": "skipped" if skipped else ("conflict" if conflict else "planned"),
            "sensitive": True,
            "reason": (CODEX_REASON_AUTH_NOT_SELECTED if skipped else (CODEX_REASON_AUTH_PROFILE_EXISTS if conflict else None)),
            "message": "Import Codex OAuth credentials and configure OpenAI Codex models." if credential["kind"] == "oauth" else "Import Codex OpenAI API key.",
            "details": {
                "provider": credential["provider"],
                "profileId": profile_id,
                "sourceProfileId": credential["profileId"],
                "sourceKind": "codex-auth-json",
                "credentialKind": credential["kind"],
            },
        }))
    return items


async def apply_codex_auth_item(params: dict) -> dict:
    ctx = params["ctx"]
    item = params["item"]
    source = params["source"]
    targets = params["targets"]
    if item.get("status") != "planned":
        return item
    details = item.get("details") or {}
    profile_id = details.get("profileId") if isinstance(details.get("profileId"), str) else ""
    provider = details.get("provider") if isinstance(details.get("provider"), str) else ""
    source_profile_id = details.get("sourceProfileId") if isinstance(details.get("sourceProfileId"), str) else None
    if not profile_id or not provider:
        return mark_migration_item_error(item, CODEX_REASON_MISSING_AUTH_METADATA)
    credentials = await _read_codex_auth_credentials(source)
    credential = next((c for c in credentials if c["provider"] == provider), None)
    if not credential:
        return mark_migration_item_skipped(item, CODEX_REASON_AUTH_NO_LONGER_PRESENT)
    if credential["kind"] == "oauth" and source_profile_id and credential["profileId"] != source_profile_id:
        return mark_migration_item_skipped(item, CODEX_REASON_AUTH_NO_LONGER_PRESENT)
    oauth_profile = credential["result"]["profiles"][0] if credential["kind"] == "oauth" and credential["result"].get("profiles") else None
    oauth_credential = oauth_profile.get("credential") if oauth_profile and oauth_profile.get("credential", {}).get("type") == "oauth" else None
    if credential["kind"] == "oauth" and not oauth_credential:
        return mark_migration_item_error(item, CODEX_REASON_MISSING_AUTH_METADATA)
    config_profile = _auth_profile_config_for_credential(credential, profile_id)
    if not config_profile:
        return mark_migration_item_error(item, CODEX_REASON_MISSING_AUTH_METADATA)
    if _has_current_auth_profile_config_conflict(ctx, config_profile):
        return mark_migration_item_conflict(item, CODEX_REASON_AUTH_PROFILE_EXISTS)
    conflicted = False
    wrote = False

    def updater(fresh_store: dict) -> bool:
        nonlocal conflicted, wrote
        profiles = fresh_store.setdefault("profiles", {})
        existing = profiles.get(profile_id)
        if not ctx.get("overwrite") and existing:
            if credential["kind"] == "oauth":
                matched_profile_id = _find_matching_oauth_profile(fresh_store, oauth_credential)
            else:
                matched_profile_id = _find_matching_api_key_profile(fresh_store, credential["provider"], credential["key"])
            if matched_profile_id == profile_id:
                return False
            conflicted = True
            return False
        if credential["kind"] == "oauth":
            profiles[profile_id] = {**oauth_credential, "displayName": CODEX_IMPORT_DISPLAY_NAME}
        else:
            profiles[profile_id] = {**build_api_key_credential(credential["provider"], credential["key"]), "displayName": CODEX_IMPORT_DISPLAY_NAME}
        wrote = True
        return True

    store = await update_auth_profile_store_with_lock({
        "agentDir": targets["agentDir"],
        "updater": updater,
    })
    if conflicted:
        return mark_migration_item_conflict(item, CODEX_REASON_AUTH_PROFILE_EXISTS)
    if not (store or {}).get("profiles", {}).get(profile_id):
        return mark_migration_item_error(item, CODEX_REASON_AUTH_PROFILE_WRITE_FAILED)
    if _should_return_auth_config_patch(ctx):
        config_result = "unavailable"
    elif credential["kind"] == "oauth":
        config_result = await _apply_oauth_config(ctx, credential, profile_id)
    else:
        config_result = await _apply_api_key_config(ctx, credential, profile_id)
    if config_result == "conflict":
        return mark_migration_item_conflict(item, CODEX_REASON_AUTH_PROFILE_EXISTS)
    new_details = {**details, "wroteAuthProfile": wrote, "configUpdated": config_result == "configured"}
    if _should_return_auth_config_patch(ctx):
        new_details["configPatchReturned"] = True
    return {**item, "status": "migrated", "details": new_details}


async def build_codex_auth_config_patch_items(params: dict) -> list:
    ctx = params["ctx"]
    item = params["item"]
    source = params["source"]
    if item.get("status") != "migrated" or not _should_return_auth_config_patch(ctx):
        return []
    details = item.get("details") or {}
    profile_id = details.get("profileId") if isinstance(details.get("profileId"), str) else ""
    provider = details.get("provider") if isinstance(details.get("provider"), str) else ""
    source_profile_id = details.get("sourceProfileId") if isinstance(details.get("sourceProfileId"), str) else None
    if not profile_id or not provider:
        return []
    credentials = await _read_codex_auth_credentials(source)
    credential = next((c for c in credentials if c["provider"] == provider), None)
    if not credential:
        return []
    if credential["kind"] == "oauth" and source_profile_id and credential["profileId"] != source_profile_id:
        return []
    if credential["kind"] == "oauth":
        next_cfg = _apply_oauth_config_to_config(ctx["config"], credential, profile_id)
    else:
        next_cfg = _apply_api_key_config_to_config(ctx["config"], credential, profile_id)
    items = []
    if next_cfg.get("auth"):
        items.append(create_migration_item({
            "id": f"{item['id']}:config:auth",
            "kind": "config",
            "action": "merge",
            "status": "migrated",
            "target": "auth",
            "message": "Configure imported Codex auth profile.",
            "details": {"path": ["auth"], "value": next_cfg["auth"]},
        }))
    agents = next_cfg.get("agents") or {}
    if agents.get("defaults"):
        items.append(create_migration_item({
            "id": f"{item['id']}:config:agents-defaults",
            "kind": "config",
            "action": "merge",
            "status": "migrated",
            "target": "agents.defaults",
            "message": "Configure imported Codex models.",
            "details": {"path": ["agents", "defaults"], "value": agents["defaults"]},
        }))
    return items
