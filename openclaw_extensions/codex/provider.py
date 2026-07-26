"""Codex provider plugin and live app-server model catalog discovery."""

from __future__ import annotations

import os
from collections.abc import Awaitable, Callable
from typing import Any

from openclaw.packages.normalization_core import is_record
from openclaw_extensions.codex.prompt_overlay import resolve_codex_system_prompt_contribution
from openclaw_extensions.codex.provider_catalog import (
    CODEX_APP_SERVER_AUTH_MARKER,
    CODEX_BASE_URL,
    CODEX_PROVIDER_ID,
    FALLBACK_CODEX_MODELS,
    build_codex_model_definition,
    build_codex_provider_config,
)
from openclaw_extensions.codex.src.app_server.config import (
    read_codex_plugin_config,
    resolve_codex_app_server_runtime_options,
)
from openclaw_extensions.codex.src.app_server.rate_limits import (
    build_codex_app_server_usage_snapshot,
)

DEFAULT_DISCOVERY_TIMEOUT_MS = 2500
LIVE_DISCOVERY_ENV = "OPENCLAW_CODEX_DISCOVERY_LIVE"
MODEL_DISCOVERY_PAGE_LIMIT = 100
CODEX_APP_SERVER_SETUP_METHOD_ID = "app-server"
CODEX_DEFAULT_MODEL_REF = f"{CODEX_PROVIDER_ID}/{FALLBACK_CODEX_MODELS[0]['id']}"


def _resolve_plugin_config_object(config: dict[str, Any] | None, plugin_id: str) -> dict[str, Any] | None:
    if not is_record(config):
        return None
    plugins = config.get("plugins")
    if not is_record(plugins):
        return None
    entries = plugins.get("entries")
    if not is_record(entries):
        return None
    entry = entries.get(plugin_id)
    if not is_record(entry):
        return None
    plugin_config = entry.get("config")
    return plugin_config if is_record(plugin_config) else None


def _normalize_model_compat(model: dict[str, Any]) -> dict[str, Any]:
    return dict(model)


def _should_default_to_reasoning_model(model_id: str) -> bool:
    lower = model_id.lower()
    return lower.startswith(("gpt-5", "o1", "o3", "o4"))


def _is_known_xhigh_codex_model(model_id: str) -> bool:
    lower = model_id.strip().lower()
    return lower.startswith(("gpt-5", "o3", "o4")) or "codex" in lower


def is_modern_codex_model(model_id: str) -> bool:
    """Return True for Codex models that use the modern reasoning effort enum."""
    lower = model_id.strip().lower()
    return lower in {
        "gpt-5.5",
        "gpt-5.4",
        "gpt-5.4-mini",
        "gpt-5.3-codex-spark",
    }


def _normalize_timeout_ms(value: Any) -> int:
    if isinstance(value, (int, float)) and value > 0:
        return int(value)
    return DEFAULT_DISCOVERY_TIMEOUT_MS


def _should_skip_live_discovery(env: dict[str, str] | None = None) -> bool:
    env_map = env if env is not None else os.environ
    override = (env_map.get(LIVE_DISCOVERY_ENV) or "").strip().lower()
    if override in {"0", "false"}:
        return True
    return bool(env_map.get("VITEST")) and override != "1"


def _resolve_codex_dynamic_model(model_id: str) -> dict[str, Any] | None:
    model = model_id.strip()
    if not model:
        return None
    fallback_model = next((entry for entry in FALLBACK_CODEX_MODELS if entry["id"] == model), None)
    return _normalize_model_compat(
        {
            **build_codex_model_definition(
                {
                    "id": model,
                    "model": model,
                    "inputModalities": fallback_model["inputModalities"] if fallback_model else ["text"],
                    "supportedReasoningEfforts": (
                        fallback_model["supportedReasoningEfforts"]
                        if fallback_model
                        else (["medium"] if _should_default_to_reasoning_model(model) else [])
                    ),
                }
            ),
            "provider": CODEX_PROVIDER_ID,
            "baseUrl": CODEX_BASE_URL,
        }
    )


async def _list_models_best_effort(
    *,
    list_models: Callable[..., Awaitable[dict[str, Any]]],
    timeout_ms: int,
    start_options: dict[str, Any],
    on_discovery_failure: Callable[[Any], None] | None = None,
) -> list[dict[str, Any]]:
    try:
        models: list[dict[str, Any]] = []
        cursor: str | None = None
        while True:
            result = await list_models(
                timeoutMs=timeout_ms,
                limit=MODEL_DISCOVERY_PAGE_LIMIT,
                cursor=cursor,
                startOptions=start_options,
                sharedClient=False,
            )
            models.extend(
                model
                for model in result.get("models", [])
                if is_record(model) and not model.get("hidden")
            )
            cursor = result.get("nextCursor")
            if not cursor:
                break
        return models
    except Exception as error:  # noqa: BLE001
        if on_discovery_failure is not None:
            on_discovery_failure(error)
        return []


async def _list_codex_app_server_models_lazy(**options: Any) -> dict[str, Any]:
    from openclaw_extensions.codex.src.app_server.models import list_codex_app_server_models

    return await list_codex_app_server_models(**options)


async def _request_codex_app_server_rate_limits_lazy(**options: Any) -> Any:
    from openclaw_extensions.codex.src.app_server.request import request_codex_app_server_json

    return await request_codex_app_server_json(
        method="account/rateLimits/read",
        timeoutMs=options.get("timeoutMs"),
        agentDir=options.get("agentDir"),
        authProfileId=options.get("authProfileId"),
        config=options.get("config"),
        startOptions=options.get("startOptions"),
        isolated=True,
    )


async def build_codex_provider_catalog(options: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build the Codex model catalog from live discovery with static fallback."""
    options = options or {}
    config = read_codex_plugin_config(options.get("pluginConfig"))
    app_server = resolve_codex_app_server_runtime_options({"pluginConfig": options.get("pluginConfig")})
    discovery = config.get("discovery") if is_record(config.get("discovery")) else {}
    timeout_ms = _normalize_timeout_ms(discovery.get("timeoutMs"))
    discovered: list[dict[str, Any]] = []
    if discovery.get("enabled") is not False and not _should_skip_live_discovery(options.get("env")):
        list_models = options.get("listModels") or _list_codex_app_server_models_lazy
        discovered = await _list_models_best_effort(
            list_models=list_models,
            timeout_ms=timeout_ms,
            start_options=app_server["start"],
            on_discovery_failure=options.get("onDiscoveryFailure"),
        )
    models = discovered if discovered else FALLBACK_CODEX_MODELS
    return {"provider": build_codex_provider_config(models)}


def build_codex_provider(options: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build the Codex provider plugin descriptor."""
    options = options or {}
    startup_plugin_config = options.get("pluginConfig")

    async def catalog_run(ctx: dict[str, Any]) -> dict[str, Any]:
        runtime_plugin_config = _resolve_plugin_config_object(ctx.get("config"), CODEX_PROVIDER_ID)
        plugin_config = runtime_plugin_config if runtime_plugin_config is not None else (
            startup_plugin_config if not ctx.get("config") else None
        )
        return await build_codex_provider_catalog(
            {
                "env": ctx.get("env"),
                "pluginConfig": plugin_config,
                "listModels": options.get("listModels"),
            }
        )

    async def static_catalog_run(_ctx: dict[str, Any] | None = None) -> dict[str, Any]:
        return {"provider": build_codex_provider_config(FALLBACK_CODEX_MODELS)}

    async def fetch_usage_snapshot(ctx: dict[str, Any]) -> dict[str, Any] | None:
        if ctx.get("token") != CODEX_APP_SERVER_AUTH_MARKER:
            return None
        runtime_plugin_config = _resolve_plugin_config_object(ctx.get("config"), CODEX_PROVIDER_ID)
        plugin_config = runtime_plugin_config if runtime_plugin_config is not None else (
            startup_plugin_config if not ctx.get("config") else None
        )
        app_server = resolve_codex_app_server_runtime_options({"pluginConfig": plugin_config})
        read_rate_limits = options.get("readRateLimits") or _request_codex_app_server_rate_limits_lazy
        rate_limits = await read_rate_limits(
            timeoutMs=ctx.get("timeoutMs"),
            agentDir=ctx.get("agentDir"),
            authProfileId=ctx.get("authProfileId"),
            config=ctx.get("config"),
            startOptions=app_server["start"],
        )
        return build_codex_app_server_usage_snapshot(rate_limits)

    async def auth_run(_ctx: dict[str, Any] | None = None) -> dict[str, Any]:
        return {"profiles": [], "defaultModel": CODEX_DEFAULT_MODEL_REF}

    def resolve_thinking_profile(params: dict[str, Any]) -> dict[str, Any]:
        model_id = str(params.get("modelId") or "")
        levels: list[dict[str, str]] = [
            {"id": "off"},
            {"id": "minimal"},
            {"id": "low"},
            {"id": "medium"},
            {"id": "high"},
        ]
        if _is_known_xhigh_codex_model(model_id):
            levels.append({"id": "xhigh"})
        return {"levels": levels}

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
                "run": auth_run,
            }
        ],
        "catalog": {"order": "late", "run": catalog_run},
        "staticCatalog": {"order": "late", "run": static_catalog_run},
        "resolveDynamicModel": lambda ctx: _resolve_codex_dynamic_model(str(ctx.get("modelId") or "")),
        "resolveSyntheticAuth": lambda _ctx=None: {
            "apiKey": CODEX_APP_SERVER_AUTH_MARKER,
            "source": "codex-app-server",
            "mode": "token",
        },
        "fetchUsageSnapshot": fetch_usage_snapshot,
        "resolveThinkingProfile": resolve_thinking_profile,
        "resolveSystemPromptContribution": lambda params: resolve_codex_system_prompt_contribution(params),
        "isModernModelRef": lambda params: is_modern_codex_model(str(params.get("modelId") or "")),
    }
