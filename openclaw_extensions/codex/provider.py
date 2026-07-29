from openclaw.plugin_sdk.core import create_subsystem_logger
from openclaw.plugin_sdk.plugin_config_runtime import resolve_plugin_config_object
from openclaw.plugin_sdk.provider_model_shared import normalize_model_compat

from .prompt_overlay import resolve_codex_system_prompt_contribution
from .provider_catalog import (
    CODEX_APP_SERVER_AUTH_MARKER,
    CODEX_BASE_URL,
    CODEX_PROVIDER_ID,
    FALLBACK_CODEX_MODELS,
    build_codex_model_definition,
    build_codex_provider_config,
)

DEFAULT_DISCOVERY_TIMEOUT_MS = 2500
LIVE_DISCOVERY_ENV = "OPENCLAW_CODEX_DISCOVERY_LIVE"
MODEL_DISCOVERY_PAGE_LIMIT = 100
CODEX_APP_SERVER_SETUP_METHOD_ID = "app-server"
CODEX_DEFAULT_MODEL_REF = f"{CODEX_PROVIDER_ID}/{FALLBACK_CODEX_MODELS[0]['id']}"
codex_catalog_log = create_subsystem_logger("codex/catalog")


def build_codex_provider(options: dict = None) -> dict:
    options = options or {}
    list_models = options.get("listModels")
    read_rate_limits = options.get("readRateLimits")

    async def _catalog_run(ctx):
        runtime_plugin_config = resolve_plugin_config_object(ctx.get("config"), CODEX_PROVIDER_ID)
        plugin_config = runtime_plugin_config if runtime_plugin_config is not None else (None if ctx.get("config") else options.get("pluginConfig"))
        return await build_codex_provider_catalog({
            "env": ctx.get("env"),
            "pluginConfig": plugin_config,
            "listModels": list_models,
        })

    async def _static_catalog_run(_ctx=None):
        return {"provider": build_codex_provider_config(FALLBACK_CODEX_MODELS)}

    async def _fetch_usage_snapshot(ctx):
        if ctx.get("token") != CODEX_APP_SERVER_AUTH_MARKER:
            return None
        from .src.app_server.config import resolve_codex_app_server_runtime_options

        runtime_plugin_config = resolve_plugin_config_object(ctx.get("config"), CODEX_PROVIDER_ID)
        plugin_config = runtime_plugin_config if runtime_plugin_config is not None else (None if ctx.get("config") else options.get("pluginConfig"))
        app_server = resolve_codex_app_server_runtime_options({"pluginConfig": plugin_config})
        rate_limit_reader = read_rate_limits or _request_codex_app_server_rate_limits_lazy
        rate_limits = await rate_limit_reader({
            "timeoutMs": ctx.get("timeoutMs"),
            "agentDir": ctx.get("agentDir"),
            **({"authProfileId": ctx["authProfileId"]} if ctx.get("authProfileId") else {}),
            "config": ctx.get("config"),
            "startOptions": app_server["start"],
        })
        from .src.app_server.rate_limits import build_codex_app_server_usage_snapshot

        return build_codex_app_server_usage_snapshot(rate_limits)

    def _resolve_thinking_profile(params):
        levels = [
            {"id": "off"},
            {"id": "minimal"},
            {"id": "low"},
            {"id": "medium"},
            {"id": "high"},
        ]
        if _is_known_xhigh_codex_model(params["modelId"]):
            levels.append({"id": "xhigh"})
        return {"levels": levels}

    def _resolve_system_prompt_contribution(params):
        return resolve_codex_system_prompt_contribution({"config": params.get("config"), "modelId": params["modelId"]})

    return {
        "id": CODEX_PROVIDER_ID,
        "label": "Codex",
        "docsPath": "/providers/models",
        "auth": [
            {
                "id": CODEX_APP_SERVER_SETUP_METHOD_ID,
                "label": "Codex app-server",
                "hint": "Use the Codex app-server runtime and managed model catalog.",
                "kind": "custom",
                "wizard": {
                    "choiceId": CODEX_PROVIDER_ID,
                    "choiceLabel": "Codex app-server",
                    "choiceHint": "Use the Codex app-server runtime and managed model catalog.",
                    "assistantPriority": -40,
                    "groupId": CODEX_PROVIDER_ID,
                    "groupLabel": "Codex",
                    "groupHint": "Codex app-server model provider",
                    "onboardingScopes": ["text-inference"],
                },
                "run": lambda: {"profiles": [], "defaultModel": CODEX_DEFAULT_MODEL_REF},
            }
        ],
        "catalog": {"order": "late", "run": _catalog_run},
        "staticCatalog": {"order": "late", "run": _static_catalog_run},
        "resolveDynamicModel": lambda ctx: _resolve_codex_dynamic_model(ctx["modelId"]),
        "resolveSyntheticAuth": lambda: {
            "apiKey": CODEX_APP_SERVER_AUTH_MARKER,
            "source": "codex-app-server",
            "mode": "token",
        },
        "fetchUsageSnapshot": _fetch_usage_snapshot,
        "resolveThinkingProfile": _resolve_thinking_profile,
        "resolveSystemPromptContribution": _resolve_system_prompt_contribution,
        "isModernModelRef": lambda params: _is_modern_codex_model(params["modelId"]),
    }


async def build_codex_provider_catalog(options: dict = None):
    import os

    options = options or {}
    from .src.app_server.config import read_codex_plugin_config, resolve_codex_app_server_runtime_options

    config = read_codex_plugin_config(options.get("pluginConfig"))
    app_server = resolve_codex_app_server_runtime_options({"pluginConfig": options.get("pluginConfig")})
    timeout_ms = _normalize_timeout_ms((config.get("discovery") or {}).get("timeoutMs"))
    discovered = []
    if (config.get("discovery") or {}).get("enabled") is not False and not _should_skip_live_discovery(options.get("env") or os.environ):
        discovered = await _list_models_best_effort({
            "listModels": options.get("listModels") or _list_codex_app_server_models_lazy,
            "timeoutMs": timeout_ms,
            "startOptions": app_server["start"],
            "onDiscoveryFailure": options.get("onDiscoveryFailure"),
        })
    return {
        "provider": build_codex_provider_config(discovered if discovered else FALLBACK_CODEX_MODELS)
    }


def _resolve_codex_dynamic_model(model_id: str):
    model_id = (model_id or "").strip()
    if not model_id:
        return None
    fallback_model = next((model for model in FALLBACK_CODEX_MODELS if model["id"] == model_id), None)
    return normalize_model_compat({
        **build_codex_model_definition({
            "id": model_id,
            "model": model_id,
            "inputModalities": (fallback_model or {}).get("inputModalities", ["text"]),
            "supportedReasoningEfforts": (fallback_model or {}).get("supportedReasoningEfforts", (["medium"] if _should_default_to_reasoning_model(model_id) else [])),
        }),
        "provider": CODEX_PROVIDER_ID,
        "baseUrl": CODEX_BASE_URL,
    })


async def _list_models_best_effort(params: dict):
    try:
        models = []
        cursor = None
        while True:
            result = await params["listModels"]({
                "timeoutMs": params["timeoutMs"],
                "limit": MODEL_DISCOVERY_PAGE_LIMIT,
                "cursor": cursor,
                "startOptions": params["startOptions"],
                "sharedClient": False,
            })
            for model in result["models"]:
                if not model.get("hidden"):
                    models.append(model)
            cursor = result.get("nextCursor")
            if not cursor:
                break
        return models
    except Exception as error:
        if params.get("onDiscoveryFailure"):
            params["onDiscoveryFailure"](error)
        codex_catalog_log.debug("codex model discovery failed; using fallback catalog", {
            "error": str(error),
        })
        return []


async def _list_codex_app_server_models_lazy(options: dict):
    from .src.app_server.models import list_codex_app_server_models

    return await list_codex_app_server_models(options)


async def _request_codex_app_server_rate_limits_lazy(options: dict):
    from .src.app_server.request import request_codex_app_server_json

    return await request_codex_app_server_json({
        "method": "account/rateLimits/read",
        "timeoutMs": options["timeoutMs"],
        "agentDir": options.get("agentDir"),
        **({"authProfileId": options["authProfileId"]} if options.get("authProfileId") else {}),
        "config": options.get("config"),
        "startOptions": options.get("startOptions"),
        "isolated": True,
    })


def _normalize_timeout_ms(value) -> int:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        import math

        if math.isfinite(value) and value > 0:
            return value
    return DEFAULT_DISCOVERY_TIMEOUT_MS


def _should_skip_live_discovery(env) -> bool:
    override = (env.get(LIVE_DISCOVERY_ENV) or "").strip().lower()
    if override == "0" or override == "false":
        return True
    return bool(env.get("VITEST")) and override != "1"


def _should_default_to_reasoning_model(model_id: str) -> bool:
    lower = model_id.lower()
    return (
        lower.startswith("gpt-5")
        or lower.startswith("o1")
        or lower.startswith("o3")
        or lower.startswith("o4")
    )


def _is_known_xhigh_codex_model(model_id: str) -> bool:
    lower = (model_id or "").strip().lower()
    return (
        lower.startswith("gpt-5")
        or lower.startswith("o3")
        or lower.startswith("o4")
        or "codex" in lower
    )


def _is_modern_codex_model(model_id: str) -> bool:
    lower = (model_id or "").strip().lower()
    return (
        lower == "gpt-5.5"
        or lower == "gpt-5.4"
        or lower == "gpt-5.4-mini"
        or lower == "gpt-5.3-codex-spark"
    )
