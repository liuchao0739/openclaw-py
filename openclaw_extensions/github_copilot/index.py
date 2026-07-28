from __future__ import annotations

import asyncio
from typing import Any

from openclaw.plugin_sdk.plugin_entry import OpenClawPluginApi, define_plugin_entry
from openclaw.plugin_sdk.provider_auth import (
    apply_auth_profile_config,
    coerce_secret_ref,
    ensure_auth_profile_store,
    list_profiles_for_provider,
    resolve_default_secret_provider_alias,
    upsert_auth_profile_with_lock,
)
from openclaw.plugin_sdk.provider_catalog_shared import get_cached_live_catalog_value
from openclaw.utils.normalize_secret_input import normalize_optional_secret_input

from openclaw_extensions.github_copilot.auth import resolve_first_github_token
from openclaw_extensions.github_copilot.embeddings import (
    github_copilot_memory_embedding_provider_adapter,
)
from openclaw_extensions.github_copilot.model_metadata import (
    resolve_copilot_extended_thinking_levels,
)
from openclaw_extensions.github_copilot.models import (
    PROVIDER_ID,
    fetch_copilot_model_catalog,
    resolve_copilot_forward_compat_model,
)
from openclaw_extensions.github_copilot.replay_policy import (
    build_github_copilot_replay_policy,
    sanitize_github_copilot_replay_history,
)
from openclaw_extensions.github_copilot.stream import wrap_copilot_provider_stream

COPILOT_ENV_VARS = ["COPILOT_GITHUB_TOKEN", "GH_TOKEN", "GITHUB_TOKEN"]
DEFAULT_COPILOT_MODEL = "github-copilot/claude-opus-4.7"
DEFAULT_COPILOT_PROFILE_ID = "github-copilot:github"


def _load_github_copilot_runtime():
    from openclaw_extensions.github_copilot.register_runtime import (
        DEFAULT_COPILOT_API_BASE_URL,
        resolve_copilot_api_token,
    )
    return {
        "DEFAULT_COPILOT_API_BASE_URL": DEFAULT_COPILOT_API_BASE_URL,
        "resolve_copilot_api_token": resolve_copilot_api_token,
    }


def _apply_copilot_default_model(cfg: dict[str, Any]) -> dict[str, Any]:
    agents = cfg.get("agents", {})
    defaults = agents.get("defaults", {}) if isinstance(agents, dict) else {}
    existing_model = defaults.get("model") if isinstance(defaults, dict) else None
    existing_primary = ""
    if isinstance(existing_model, str):
        existing_primary = existing_model.strip()
    elif isinstance(existing_model, dict) and isinstance(existing_model.get("primary"), str):
        existing_primary = existing_model["primary"].strip()
    if existing_primary:
        return cfg

    fallbacks = None
    if isinstance(existing_model, dict) and existing_model and "fallbacks" in existing_model:
        fallbacks = existing_model.get("fallbacks")

    new_cfg = dict(cfg)
    new_agents = dict(agents) if isinstance(agents, dict) else {}
    new_defaults = dict(defaults) if isinstance(defaults, dict) else {}
    new_defaults["model"] = {
        **({"fallbacks": fallbacks} if fallbacks else {}),
        "primary": DEFAULT_COPILOT_MODEL,
    }
    models_dict = new_defaults.get("models", {})
    if not isinstance(models_dict, dict):
        models_dict = {}
    models_dict[DEFAULT_COPILOT_MODEL] = models_dict.get(DEFAULT_COPILOT_MODEL, {})
    new_defaults["models"] = models_dict
    new_agents["defaults"] = new_defaults
    new_cfg["agents"] = new_agents
    return new_cfg


def _resolve_existing_copilot_token_profile_id(agent_dir: str | None) -> str | None:
    auth_store = ensure_auth_profile_store(agent_dir, {"allowKeychainPrompt": False})
    profile_ids = list_profiles_for_provider(auth_store, PROVIDER_ID)
    for profile_id in profile_ids:
        profile = auth_store.profiles.get(profile_id)
        if not isinstance(profile, dict) or profile.get("type") != "token":
            continue
        token_val = normalize_optional_secret_input(profile.get("token"))
        token_ref = coerce_secret_ref(profile.get("tokenRef"))
        if token_val or (token_ref and token_ref.get("id", "").strip()):
            return profile_id
    return None


def _resolve_existing_copilot_auth_result(agent_dir: str | None) -> dict[str, Any] | None:
    profile_id = _resolve_existing_copilot_token_profile_id(agent_dir)
    if not profile_id:
        return None
    auth_store = ensure_auth_profile_store(agent_dir, {"allowKeychainPrompt": False})
    credential = auth_store.profiles.get(profile_id)
    if not isinstance(credential, dict) or credential.get("type") != "token":
        return None
    return {
        "profiles": [
            {
                "profileId": profile_id,
                "credential": credential,
            },
        ],
        "defaultModel": DEFAULT_COPILOT_MODEL,
    }


async def _resolve_copilot_non_interactive_token(
    ctx: dict[str, Any],
    flag_value: str | None,
) -> Any:
    async def resolve_from_env_chain():
        for env_var in COPILOT_ENV_VARS:
            resolved = await ctx["resolveApiKey"]({
                "provider": PROVIDER_ID,
                "flagName": "--github-copilot-token",
                "envVar": env_var,
                "envVarName": env_var,
                "allowProfile": False,
                "required": False,
            })
            if resolved:
                return resolved
        return None

    opts = ctx.get("opts", {})
    if opts.get("secretInputMode") == "ref":
        resolved = await resolve_from_env_chain()
        if resolved:
            return resolved
        if flag_value:
            ctx["runtime"]["error"](
                "--github-copilot-token cannot be used with --secret-input-mode ref "
                "unless COPILOT_GITHUB_TOKEN, GH_TOKEN, or GITHUB_TOKEN is set in env.\n"
                "Set one of those env vars and omit --github-copilot-token, or use --secret-input-mode plaintext.",
            )
            ctx["runtime"]["exit"](1)
        return None

    primary = await ctx["resolveApiKey"]({
        "provider": PROVIDER_ID,
        "flagValue": flag_value,
        "flagName": "--github-copilot-token",
        "envVar": COPILOT_ENV_VARS[0],
        "envVarName": COPILOT_ENV_VARS[0],
        "allowProfile": False,
        "required": False,
    })
    if primary or flag_value:
        return primary

    for env_var in COPILOT_ENV_VARS[1:]:
        resolved = await ctx["resolveApiKey"]({
            "provider": PROVIDER_ID,
            "flagName": "--github-copilot-token",
            "envVar": env_var,
            "envVarName": env_var,
            "allowProfile": False,
            "required": False,
        })
        if resolved:
            return resolved
    return None


async def _run_github_copilot_non_interactive_auth(
    ctx: dict[str, Any],
) -> dict[str, Any] | None:
    opts = ctx.get("opts", {})
    flag_value = normalize_optional_secret_input(opts.get("githubCopilotToken"))
    resolved = await _resolve_copilot_non_interactive_token(ctx, flag_value)

    profile_id = DEFAULT_COPILOT_PROFILE_ID
    if resolved:
        use_token_ref = opts.get("secretInputMode") == "ref" and resolved.get("source") == "env"
        if use_token_ref and not resolved.get("envVarName"):
            ctx["runtime"]["error"](
                '--secret-input-mode ref requires an explicit environment variable for provider "github-copilot".\n'
                "Set COPILOT_GITHUB_TOKEN in env and retry, or use --secret-input-mode plaintext.",
            )
            ctx["runtime"]["exit"](1)
            return None
        credential: dict[str, Any]
        if use_token_ref:
            credential = {
                "type": "token",
                "provider": PROVIDER_ID,
                "tokenRef": {
                    "source": "env",
                    "provider": resolve_default_secret_provider_alias(
                        ctx.get("baseConfig"), "env",
                        prefer_first_provider_for_source=True,
                    ),
                    "id": resolved["envVarName"],
                },
            }
        else:
            credential = {
                "type": "token",
                "provider": PROVIDER_ID,
                "token": resolved["key"],
            }
        await upsert_auth_profile_with_lock({
            "profileId": profile_id,
            "credential": credential,
            "agentDir": ctx.get("agentDir"),
        })
    else:
        if flag_value and opts.get("secretInputMode") == "ref":
            return None
        existing_profile_id = _resolve_existing_copilot_token_profile_id(ctx.get("agentDir"))
        if not existing_profile_id:
            ctx["runtime"]["error"](
                "Missing --github-copilot-token (or COPILOT_GITHUB_TOKEN / GH_TOKEN / GITHUB_TOKEN env var) "
                "for --auth-choice github-copilot.",
            )
            ctx["runtime"]["exit"](1)
            return None
        profile_id = existing_profile_id

    return _apply_copilot_default_model(
        apply_auth_profile_config(ctx.get("config"), {
            "profileId": profile_id,
            "provider": PROVIDER_ID,
            "mode": "token",
        })
    )


def _resolve_current_plugin_config(config: dict[str, Any] | None, startup_config: dict[str, Any]) -> dict[str, Any]:
    if config:
        plugins = config.get("plugins", {})
        if isinstance(plugins, dict):
            runtime_config = plugins.get("github-copilot")
            if runtime_config and isinstance(runtime_config, dict):
                return runtime_config
    return startup_config


async def _run_github_copilot_catalog(ctx: dict[str, Any]) -> dict[str, Any] | None:
    config = ctx.get("config")
    startup_config = ctx.get("_startupPluginConfig", {})
    plugin_config = _resolve_current_plugin_config(config, startup_config)
    discovery_enabled = plugin_config.get("discovery", {}).get("enabled") if isinstance(plugin_config, dict) else None
    if discovery_enabled is False:
        return None

    runtime = _load_github_copilot_runtime()
    default_base = runtime["DEFAULT_COPILOT_API_BASE_URL"]
    resolve_token = runtime["resolve_copilot_api_token"]

    token_result = await resolve_first_github_token({
        "agentDir": ctx.get("agentDir"),
        "config": config,
        "env": ctx.get("env"),
    })
    github_token = token_result.get("githubToken", "")
    has_profile = token_result.get("hasProfile", False)

    if not has_profile and not github_token:
        return None

    base_url = default_base
    copilot_api_token = None
    if github_token:
        try:
            token = await resolve_token({
                "githubToken": github_token,
                "env": ctx.get("env"),
            })
            base_url = token.get("baseUrl", default_base)
            copilot_api_token = token.get("token")
        except Exception:
            base_url = default_base

    discovered_models = []
    if copilot_api_token:
        try:
            discovered_models = await get_cached_live_catalog_value({
                "keyParts": [PROVIDER_ID, "models", base_url, copilot_api_token],
                "load": lambda: fetch_copilot_model_catalog({
                    "copilotApiToken": copilot_api_token,
                    "baseUrl": base_url,
                }),
            })
        except Exception:
            discovered_models = []

    return {
        "provider": {
            "baseUrl": base_url,
            "models": discovered_models,
        },
    }


async def _run_github_copilot_unified_live_catalog(ctx: dict[str, Any]) -> list[dict[str, Any]] | None:
    result = await _run_github_copilot_catalog(ctx)
    if not result or "provider" not in result:
        return None
    models = result["provider"].get("models", [])
    entries = []
    for model in models:
        entry = {
            "kind": "text",
            "provider": PROVIDER_ID,
            "model": model.get("id", ""),
            "source": "live",
        }
        if model.get("name"):
            entry["label"] = model["name"]
        entries.append(entry)
    return entries


async def _run_github_copilot_auth(ctx: dict[str, Any]) -> dict[str, Any]:
    existing = _resolve_existing_copilot_auth_result(ctx.get("agentDir"))
    if existing:
        run_login = await ctx["prompter"]["confirm"]({
            "message": "GitHub Copilot auth already exists. Re-run login?",
            "initialValue": False,
        })
        if not run_login:
            return existing

    await ctx["prompter"]["note"](
        "This will open a GitHub device login to authorize Copilot.\n"
        "Requires an active GitHub Copilot subscription.",
        "GitHub Copilot",
    )

    from openclaw_extensions.github_copilot.login import run_github_copilot_device_flow

    async def show_code(args: dict[str, Any]) -> None:
        expires_in_minutes = max(1, round(args.get("expiresInMs", 0) / 60000))
        await ctx["prompter"]["note"](
            f"Open this URL in your browser and enter the code below.\n"
            f"URL: {args['verificationUrl']}\n"
            f"Code: {args['userCode']}\n"
            f"Code expires in {expires_in_minutes} minutes. Never share it.\n\n"
            "If a browser does not open automatically after you continue, copy the URL manually.",
            "Authorize GitHub Copilot",
        )

    result = await run_github_copilot_device_flow({
        "showCode": show_code,
        "openUrl": lambda url: ctx["openUrl"](url),
    })

    if result.get("status") == "access_denied":
        await ctx["prompter"]["note"]("GitHub Copilot login was cancelled.", "GitHub Copilot")
        return {"profiles": []}

    if result.get("status") == "expired":
        await ctx["prompter"]["note"](
            "The GitHub device code expired. Retry login to get a new code.",
            "GitHub Copilot",
        )
        return {"profiles": []}

    return {
        "profiles": [
            {
                "profileId": DEFAULT_COPILOT_PROFILE_ID,
                "credential": {
                    "type": "token",
                    "provider": PROVIDER_ID,
                    "token": result["accessToken"],
                },
            },
        ],
        "defaultModel": DEFAULT_COPILOT_MODEL,
    }


def _resolve_thinking_profile(ctx: dict[str, Any]) -> dict[str, Any]:
    model_id = ctx.get("modelId", "")
    compat = ctx.get("compat")
    extended_levels = resolve_copilot_extended_thinking_levels(model_id, compat)
    return {
        "levels": [
            {"id": "off"},
            {"id": "minimal"},
            {"id": "low"},
            {"id": "medium"},
            {"id": "high"},
            *[{"id": level} for level in extended_levels],
        ],
    }


def _register(api: OpenClawPluginApi) -> None:
    startup_plugin_config = (api.plugin_config or {})

    async def prepare_runtime_auth(ctx: dict[str, Any]) -> dict[str, Any]:
        runtime = _load_github_copilot_runtime()
        token = await runtime["resolve_copilot_api_token"]({
            "githubToken": ctx.get("apiKey"),
            "env": ctx.get("env"),
        })
        return {
            "apiKey": token.get("token"),
            "baseUrl": token.get("baseUrl"),
            "expiresAt": token.get("expiresAt"),
        }

    async def fetch_usage_snapshot(ctx: dict[str, Any]) -> dict[str, Any]:
        from openclaw_extensions.github_copilot.usage import fetch_copilot_usage
        return await fetch_copilot_usage(
            ctx.get("token", ""),
            ctx.get("timeoutMs", 30000),
            ctx.get("fetchFn"),
        )

    api.register_memory_embedding_provider(github_copilot_memory_embedding_provider_adapter)

    api.register_provider({
        "id": PROVIDER_ID,
        "label": "GitHub Copilot",
        "docsPath": "/providers/models",
        "envVars": COPILOT_ENV_VARS,
        "auth": [
            {
                "id": "device",
                "label": "GitHub device login",
                "hint": "Browser device-code flow",
                "kind": "device_code",
                "run": _run_github_copilot_auth,
                "runNonInteractive": _run_github_copilot_non_interactive_auth,
            },
        ],
        "wizard": {
            "setup": {
                "choiceId": "github-copilot",
                "choiceLabel": "GitHub Copilot",
                "choiceHint": "Device login with your GitHub account",
                "methodId": "device",
                "modelSelection": {
                    "promptWhenAuthChoiceProvided": True,
                },
            },
        },
        "catalog": {
            "order": "late",
            "run": _run_github_copilot_catalog,
        },
        "resolveDynamicModel": lambda ctx: resolve_copilot_forward_compat_model(ctx),
        "wrapStreamFn": lambda ctx: wrap_copilot_provider_stream(ctx),
        "buildReplayPolicy": lambda ctx: build_github_copilot_replay_policy(ctx.get("modelId")),
        "sanitizeReplayHistory": lambda ctx: sanitize_github_copilot_replay_history(ctx),
        "resolveThinkingProfile": _resolve_thinking_profile,
        "prepareRuntimeAuth": prepare_runtime_auth,
        "resolveUsageAuth": lambda ctx: ctx.get("resolveOAuthToken"),
        "fetchUsageSnapshot": fetch_usage_snapshot,
    })

    api.register_model_catalog_provider({
        "provider": PROVIDER_ID,
        "kinds": ["text"],
        "liveCatalog": _run_github_copilot_unified_live_catalog,
    })


default = define_plugin_entry(
    id="github-copilot",
    name="GitHub Copilot Provider",
    description="Bundled GitHub Copilot provider plugin",
    register=_register,
)
