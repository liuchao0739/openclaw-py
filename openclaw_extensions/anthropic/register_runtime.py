from __future__ import annotations

from typing import Any

from openclaw.packages.normalization_core import (
    is_record,
    normalize_lowercase_string_or_empty,
)
from openclaw.plugin_sdk.plugin_entry import OpenClawPluginApi
from openclaw.plugin_sdk.provider_auth import (
    CLAUDE_CLI_PROFILE_ID,
    apply_auth_profile_config,
    build_token_profile_id,
    create_provider_api_key_auth_method,
    list_profiles_for_provider,
    suggest_oauth_profile_id_for_legacy_default,
    upsert_auth_profile_with_lock,
    validate_anthropic_setup_token,
)
from openclaw.plugin_sdk.provider_auth_api_key import create_provider_api_key_auth_method
from openclaw.plugin_sdk.provider_stream_shared import (
    NATIVE_ANTHROPIC_REPLAY_HOOKS,
)

from .cli_auth_seam import (
    read_claude_cli_credentials_for_runtime,
    read_claude_cli_credentials_for_setup,
    read_claude_cli_credentials_for_setup_non_interactive,
)
from .cli_backend import build_anthropic_cli_backend
from .cli_catalog import build_claude_cli_catalog_entries
from .cli_constants import (
    CLAUDE_CLI_BACKEND_ID,
    CLAUDE_CLI_DEFAULT_ALLOWLIST_REFS,
    CLAUDE_CLI_DEFAULT_MODEL_REF,
    CLAUDE_CLI_OFF_THINKING_PROFILE,
)
from .cli_migration import build_anthropic_cli_migration_result
from .config_defaults import (
    apply_anthropic_config_defaults,
    normalize_anthropic_provider_config_for_provider,
)
from .media_understanding_provider import anthropic_media_understanding_provider
from .stream_wrappers import wrap_anthropic_provider_stream

PROVIDER_ID = "anthropic"
_DEFAULT_ANTHROPIC_MODEL = "anthropic/claude-opus-4-8"
_ANTHROPIC_OPUS_48_MODEL_ID = "claude-opus-4-8"
_ANTHROPIC_OPUS_48_DOT_MODEL_ID = "claude-opus-4.8"
_ANTHROPIC_OPUS_47_MODEL_ID = "claude-opus-4-7"
_ANTHROPIC_OPUS_47_DOT_MODEL_ID = "claude-opus-4.7"
_ANTHROPIC_GA_1M_CONTEXT_TOKENS = 1_048_576
_ANTHROPIC_FABLE_CONTEXT_TOKENS = 1_000_000
_ANTHROPIC_MODERN_MAX_OUTPUT_TOKENS = 128_000
_ANTHROPIC_OPUS_46_MODEL_ID = "claude-opus-4-6"
_ANTHROPIC_OPUS_46_DOT_MODEL_ID = "claude-opus-4.6"
_ANTHROPIC_OPUS_47_TEMPLATE_MODEL_IDS = [
    _ANTHROPIC_OPUS_46_MODEL_ID,
    _ANTHROPIC_OPUS_46_DOT_MODEL_ID,
]
_ANTHROPIC_SONNET_46_MODEL_ID = "claude-sonnet-4-6"
_ANTHROPIC_SONNET_46_DOT_MODEL_ID = "claude-sonnet-4.6"
_ANTHROPIC_SETUP_TOKEN_NOTE_LINES = [
    "Anthropic setup-token auth is supported in OpenClaw.",
    "OpenClaw prefers Claude CLI reuse when it is available on the host.",
    "Anthropic staff told us this OpenClaw path is allowed again.",
    "If you want a direct API billing path instead, use openclaw models auth login --provider anthropic --method api-key --set-default or openclaw models auth login --provider anthropic --method cli --set-default.",
]

_CLAUDE_CLI_CANONICAL_ALLOWLIST_REFS = [
    f"anthropic/{ref[len(CLAUDE_CLI_BACKEND_ID) + 1:]}"
    if ref.startswith(f"{CLAUDE_CLI_BACKEND_ID}/")
    else ref
    for ref in CLAUDE_CLI_DEFAULT_ALLOWLIST_REFS
]

_CLAUDE_CLI_CANONICAL_DEFAULT_MODEL_REF = (
    f"anthropic/{CLAUDE_CLI_DEFAULT_MODEL_REF[len(CLAUDE_CLI_BACKEND_ID) + 1:]}"
    if CLAUDE_CLI_DEFAULT_MODEL_REF.startswith(f"{CLAUDE_CLI_BACKEND_ID}/")
    else CLAUDE_CLI_DEFAULT_MODEL_REF
)


def _normalize_anthropic_setup_token_input(value: str) -> str:
    import re
    return re.sub(r"\s+", "", value).strip()


def _resolve_anthropic_setup_token_profile_id(raw_profile_id: Any = None) -> str:
    if isinstance(raw_profile_id, str) and raw_profile_id.strip():
        trimmed = raw_profile_id.strip()
        if trimmed.startswith(f"{PROVIDER_ID}:"):
            return trimmed
        return build_token_profile_id({"provider": PROVIDER_ID, "name": trimmed})
    return f"{PROVIDER_ID}:default"


def _resolve_anthropic_setup_token_expiry(raw_expires_in: Any = None) -> int | None:
    if not isinstance(raw_expires_in, str) or not raw_expires_in.strip():
        return None
    try:
        from openclaw.plugin_sdk.number_runtime import (
            resolve_expires_at_ms_from_duration_ms,
        )
        from openclaw.plugin_sdk.cli_runtime import parse_duration_ms

        return resolve_expires_at_ms_from_duration_ms(
            parse_duration_ms(raw_expires_in.strip(), default_unit="d")
        )
    except ImportError:
        return None


async def _run_anthropic_setup_token_auth(
    ctx: dict[str, Any],
) -> dict[str, Any]:
    opts = ctx.get("opts", {}) if isinstance(ctx, dict) else {}
    provided_token = None
    token_value = opts.get("token")
    if isinstance(token_value, str) and token_value.strip():
        provided_token = _normalize_anthropic_setup_token_input(token_value)

    token = provided_token
    if token is None:
        prompter = ctx.get("prompter", {})
        if isinstance(prompter, dict):
            token = _normalize_anthropic_setup_token_input(
                prompter.get("text", lambda _: "")()
            )
    token_error = validate_anthropic_setup_token(token)
    if token_error:
        raise ValueError(token_error)

    profile_id = _resolve_anthropic_setup_token_profile_id(opts.get("tokenProfileId"))
    expires = _resolve_anthropic_setup_token_expiry(opts.get("tokenExpiresIn"))

    profiles: list[dict[str, Any]] = [
        {
            "profileId": profile_id,
            "credential": {
                "type": "token",
                "provider": PROVIDER_ID,
                "token": token,
            },
        }
    ]
    if expires is not None:
        profiles[0]["credential"]["expires"] = expires

    return {
        "profiles": profiles,
        "defaultModel": _DEFAULT_ANTHROPIC_MODEL,
        "notes": list(_ANTHROPIC_SETUP_TOKEN_NOTE_LINES),
    }


async def _run_anthropic_setup_token_non_interactive(
    ctx: dict[str, Any],
) -> dict[str, Any] | None:
    opts = ctx.get("opts", {}) if isinstance(ctx, dict) else {}
    raw_token = ""
    token_value = opts.get("token")
    if isinstance(token_value, str):
        raw_token = _normalize_anthropic_setup_token_input(token_value)
    token_error = validate_anthropic_setup_token(raw_token)
    if token_error:
        runtime = ctx.get("runtime", {})
        if isinstance(runtime, dict):
            error_fn = runtime.get("error")
            if callable(error_fn):
                error_fn(
                    "Anthropic setup-token auth requires --token with a valid setup-token.\n"
                    + token_error
                )
            exit_fn = runtime.get("exit")
            if callable(exit_fn):
                exit_fn(1)
        return None

    profile_id = _resolve_anthropic_setup_token_profile_id(opts.get("tokenProfileId"))
    expires = _resolve_anthropic_setup_token_expiry(opts.get("tokenExpiresIn"))

    credential: dict[str, Any] = {
        "type": "token",
        "provider": PROVIDER_ID,
        "token": raw_token,
    }
    if expires is not None:
        credential["expires"] = expires

    agent_dir = ctx.get("agentDir", "")
    if isinstance(agent_dir, str) and agent_dir:
        await upsert_auth_profile_with_lock({
            "profileId": profile_id,
            "credential": credential,
            "agentDir": agent_dir,
        })

    runtime = ctx.get("runtime", {})
    if isinstance(runtime, dict):
        log_fn = runtime.get("log")
        if callable(log_fn):
            log_fn(_ANTHROPIC_SETUP_TOKEN_NOTE_LINES[0])
            log_fn(_ANTHROPIC_SETUP_TOKEN_NOTE_LINES[1])

    config = ctx.get("config", {})
    config_with_profile = apply_auth_profile_config(config, {
        "profileId": profile_id,
        "provider": PROVIDER_ID,
        "mode": "token",
    })
    existing_model_config = {}
    agents = config_with_profile.get("agents", {})
    defaults = agents.get("defaults", {}) if isinstance(agents, dict) else {}
    if isinstance(defaults, dict):
        model = defaults.get("model")
        if isinstance(model, dict):
            existing_model_config = model

    return {
        **config_with_profile,
        "agents": {
            **agents,
            "defaults": {
                **(defaults if isinstance(defaults, dict) else {}),
                "model": {
                    **existing_model_config,
                    "primary": _DEFAULT_ANTHROPIC_MODEL,
                },
            },
        },
    }


def _resolve_anthropic_forward_compat_model(
    ctx: dict[str, Any],
) -> dict[str, Any] | None:
    model_id = ctx.get("modelId", "")
    if not isinstance(model_id, str):
        return None
    trimmed = model_id.strip()
    lower = normalize_lowercase_string_or_empty(trimmed)
    if trimmed != lower:
        return None
    is_46_model = (
        lower == _ANTHROPIC_OPUS_48_MODEL_ID
        or lower == _ANTHROPIC_OPUS_48_DOT_MODEL_ID
        or lower.startswith(f"{_ANTHROPIC_OPUS_48_MODEL_ID}-")
        or lower.startswith(f"{_ANTHROPIC_OPUS_48_DOT_MODEL_ID}-")
    )
    if not is_46_model:
        return None

    template_ids: list[str] = []
    if lower.startswith(_ANTHROPIC_OPUS_48_MODEL_ID):
        template_ids.append(lower.replace(_ANTHROPIC_OPUS_48_MODEL_ID, _ANTHROPIC_OPUS_47_MODEL_ID))
    if lower.startswith(_ANTHROPIC_OPUS_48_DOT_MODEL_ID):
        template_ids.append(lower.replace(_ANTHROPIC_OPUS_48_DOT_MODEL_ID, _ANTHROPIC_OPUS_47_DOT_MODEL_ID))
    template_ids.extend(_ANTHROPIC_OPUS_47_TEMPLATE_MODEL_IDS)

    try:
        from openclaw.plugin_sdk.provider_model_shared import clone_first_template_model

        patch = None
        provider = ctx.get("provider", "")
        if normalize_lowercase_string_or_empty(provider) == CLAUDE_CLI_BACKEND_ID:
            patch = {"provider": CLAUDE_CLI_BACKEND_ID}

        return clone_first_template_model({
            "providerId": PROVIDER_ID,
            "modelId": trimmed,
            "templateIds": template_ids,
            "ctx": ctx,
            "patch": patch,
        })
    except ImportError:
        return None


def _build_anthropic_forward_compat_model(
    ctx: dict[str, Any],
) -> dict[str, Any] | None:
    model_id = ctx.get("modelId", "")
    if not isinstance(model_id, str):
        return None
    trimmed = model_id.strip()
    lower = normalize_lowercase_string_or_empty(trimmed)
    provider = ctx.get("provider", "")
    normalized_provider = normalize_lowercase_string_or_empty(provider)

    if trimmed != lower:
        return None

    try:
        from openclaw.plugin_sdk.provider_model_shared import (
            resolve_claude_model_identity,
            supports_claude_adaptive_thinking,
        )
        from .stream_wrappers import _is_anthropic_1m_model
    except ImportError:
        return None

    try:
        from openclaw.plugin_sdk.provider_model_shared import (
            resolve_claude_fable5_model_identity,
            supports_claude_native_max_effort,
            supports_claude_native_xhigh_effort,
        )

        is_fable5 = resolve_claude_fable5_model_identity({"id": lower}) is not None
        if is_fable5 and normalized_provider != PROVIDER_ID:
            return None

        is_opus47_or_newer = supports_claude_native_xhigh_effort({"id": lower}) and not is_fable5
        is_mythos_preview = False
        supports_native_max = supports_claude_native_max_effort({"id": lower})
    except ImportError:
        is_fable5 = False
        is_opus47_or_newer = False
        is_mythos_preview = False
        supports_native_max = False

    if not is_fable5 and not _is_anthropic_1m_model(lower) and not is_mythos_preview:
        return None

    resolved_provider = CLAUDE_CLI_BACKEND_ID if normalized_provider == CLAUDE_CLI_BACKEND_ID else PROVIDER_ID

    cost = (
        {"input": 10, "output": 50, "cacheRead": 1, "cacheWrite": 12.5}
        if is_fable5
        else {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0}
    )

    context_window = _ANTHROPIC_FABLE_CONTEXT_TOKENS if is_fable5 else (
        _ANTHROPIC_GA_1M_CONTEXT_TOKENS if supports_claude_adaptive_thinking({"id": lower}) else 200_000
    )

    max_tokens = _ANTHROPIC_MODERN_MAX_OUTPUT_TOKENS if is_fable5 else 64_000

    thinking_level_map: dict[str, Any] = {}
    if supports_native_max:
        if is_mythos_preview:
            thinking_level_map["max"] = "max"
        elif is_fable5:
            thinking_level_map = {"off": "low", "minimal": "low", "max": "max"}
        elif is_opus47_or_newer:
            thinking_level_map = {"xhigh": "xhigh", "max": "max"}
        else:
            thinking_level_map = {"max": "max"}

    result: dict[str, Any] = {
        "id": trimmed,
        "name": trimmed,
        "provider": resolved_provider,
        "api": "anthropic-messages",
        "baseUrl": "https://api.anthropic.com",
        "reasoning": True,
        "input": ["text", "image"],
        "cost": cost,
        "contextWindow": context_window,
        "maxTokens": max_tokens,
    }
    if thinking_level_map:
        result["thinkingLevelMap"] = thinking_level_map
    return result


def _resolve_anthropic_forward_compat_model(
    ctx: dict[str, Any],
) -> dict[str, Any] | None:
    return (
        _resolve_anthropic_forward_compat_model(ctx)
        or _build_anthropic_forward_compat_model(ctx)
    )


def _resolve_anthropic_fixed_context_window(model_id: str) -> int | None:
    try:
        from openclaw.plugin_sdk.provider_model_shared import (
            resolve_claude_fable5_model_identity,
            supports_claude_adaptive_thinking,
        )
        if resolve_claude_fable5_model_identity({"id": model_id}) is not None:
            return _ANTHROPIC_FABLE_CONTEXT_TOKENS
        if supports_claude_adaptive_thinking({"id": model_id}):
            return _ANTHROPIC_GA_1M_CONTEXT_TOKENS
    except ImportError:
        pass
    return None


def _apply_anthropic_fixed_context_window(
    params: dict[str, Any],
) -> dict[str, Any] | None:
    fixed_context_window = _resolve_anthropic_fixed_context_window(params["contractModelId"])
    if fixed_context_window is None:
        return None
    config = params.get("config")
    provider = params.get("provider", "")
    model_id = params.get("modelId", "")
    if isinstance(config, dict):
        providers = config.get("models", {}).get("providers")
        if isinstance(providers, dict):
            normalized_provider = normalize_lowercase_string_or_empty(provider)
            normalized_model_id = normalize_lowercase_string_or_empty(model_id)
            provider_config = providers.get(normalized_provider)
            if isinstance(provider_config, dict):
                models = provider_config.get("models")
                if isinstance(models, list):
                    for model in models:
                        if isinstance(model, dict):
                            mid = model.get("id", "")
                            if normalize_lowercase_string_or_empty(mid) == normalized_model_id:
                                ctx_tokens = model.get("contextTokens")
                                cw = model.get("contextWindow")
                                if (isinstance(ctx_tokens, (int, float)) and ctx_tokens > 0) or (
                                    isinstance(cw, (int, float)) and cw > 0
                                ):
                                    return None

    model = params["model"]
    exact = _resolve_anthropic_fixed_context_window(params["contractModelId"]) == _ANTHROPIC_FABLE_CONTEXT_TOKENS
    next_context_window = exact and model.get("contextWindow", 0) or max(
        model.get("contextWindow", 0), fixed_context_window
    )
    next_context_tokens = exact and model.get("contextTokens", 0) or max(
        model.get("contextTokens", 0), fixed_context_window
    )
    if next_context_window == model.get("contextWindow") and next_context_tokens == model.get("contextTokens"):
        return None
    return {
        **model,
        "contextWindow": next_context_window,
        "contextTokens": next_context_tokens,
    }


def _normalize_anthropic_resolved_model(
    ctx: dict[str, Any],
) -> dict[str, Any] | None:
    model_id = ctx.get("modelId", "")
    params = ctx.get("params")
    provider = ctx.get("provider", "")

    try:
        from openclaw.plugin_sdk.provider_model_shared import (
            resolve_claude_model_identity,
            resolve_claude_fable5_model_identity,
            supports_claude_native_max_effort,
            supports_claude_native_xhigh_effort,
        )

        contract_model_id = resolve_claude_model_identity({
            "id": model_id,
            "params": params,
        })
        is_fable5 = resolve_claude_fable5_model_identity({"id": contract_model_id}) is not None
        if is_fable5 and normalize_lowercase_string_or_empty(provider) != PROVIDER_ID:
            return None
    except ImportError:
        contract_model_id = model_id
        is_fable5 = False

    model = ctx.get("model", {})
    if is_fable5 and not model.get("reasoning"):
        model = {**model, "reasoning": True}

    if model == ctx.get("model"):
        return None
    return model


async def _resolve_anthropic_usage_auth(
    ctx: dict[str, Any],
) -> dict[str, Any]:
    oauth_token = None
    resolve_oauth = ctx.get("resolveOAuthToken")
    if callable(resolve_oauth):
        oauth_token = await resolve_oauth()
    if oauth_token:
        return oauth_token

    resolve_api_key = ctx.get("resolveApiKeyFromConfigAndStore")
    api_key = resolve_api_key() if callable(resolve_api_key) else None
    if api_key and validate_anthropic_setup_token(api_key) is None:
        return {"token": api_key}

    return {"handled": True}


def _resolve_claude_cli_synthetic_auth() -> dict[str, Any] | None:
    credential = read_claude_cli_credentials_for_runtime()
    if not credential:
        return None
    if credential.get("type") == "oauth":
        return {
            "apiKey": credential.get("access"),
            "source": "Claude CLI native auth",
            "mode": "oauth",
            "expiresAt": credential.get("expires"),
        }
    return {
        "apiKey": credential.get("token"),
        "source": "Claude CLI native auth",
        "mode": "token",
        "expiresAt": credential.get("expires"),
    }


async def _run_anthropic_cli_migration(
    ctx: dict[str, Any],
) -> dict[str, Any]:
    credential = read_claude_cli_credentials_for_setup()
    if not credential:
        raise ValueError(
            "Claude CLI is not authenticated on this host.\n"
            "Run claude auth login first, then re-run this setup."
        )
    config = ctx.get("config", {}) if isinstance(ctx, dict) else {}
    return build_anthropic_cli_migration_result(config, credential)


async def _run_anthropic_cli_migration_non_interactive(
    ctx: dict[str, Any],
) -> dict[str, Any] | None:
    credential = read_claude_cli_credentials_for_setup_non_interactive()
    if not credential:
        runtime = ctx.get("runtime", {})
        if isinstance(runtime, dict):
            error_fn = runtime.get("error")
            if callable(error_fn):
                error_fn(
                    'Auth choice "anthropic-cli" requires Claude CLI auth on this host.\n'
                    "Run claude auth login first."
                )
            exit_fn = runtime.get("exit")
            if callable(exit_fn):
                exit_fn(1)
        return None

    config = ctx.get("config", {})
    result = build_anthropic_cli_migration_result(config, credential)
    current_defaults = config.get("agents", {}).get("defaults", {})
    current_model = current_defaults.get("model") if isinstance(current_defaults, dict) else None
    current_fallbacks = None
    if isinstance(current_model, dict) and "fallbacks" in current_model:
        current_fallbacks = current_model["fallbacks"]
    migrated_model = (
        result.get("configPatch", {}).get("agents", {}).get("defaults", {}).get("model")
    )
    migrated_fallbacks = None
    if isinstance(migrated_model, dict) and "fallbacks" in migrated_model:
        migrated_fallbacks = migrated_model["fallbacks"]
    next_fallbacks = migrated_fallbacks if isinstance(migrated_fallbacks, list) else current_fallbacks

    agents = config.get("agents", {})
    patched_agents = result.get("configPatch", {}).get("agents", {})
    patched_defaults = patched_agents.get("defaults", {}) if isinstance(patched_agents, dict) else {}

    return {
        **config,
        **result.get("configPatch", {}),
        "agents": {
            **agents,
            **patched_agents,
            "defaults": {
                **(current_defaults if isinstance(current_defaults, dict) else {}),
                **patched_defaults,
                "model": {
                    **({"fallbacks": next_fallbacks} if isinstance(next_fallbacks, list) else {}),
                    "primary": result.get("defaultModel", ""),
                },
            },
        },
    }


def build_anthropic_provider() -> dict[str, Any]:
    provider_id = PROVIDER_ID
    default_anthropic_model = _DEFAULT_ANTHROPIC_MODEL

    auth_methods: list[dict[str, Any]] = [
        {
            "id": "cli",
            "label": "Claude CLI",
            "hint": "Reuse a local Claude CLI login and run Anthropic models through the Claude CLI runtime",
            "kind": "custom",
            "wizard": {
                "choiceId": "anthropic-cli",
                "choiceLabel": "Anthropic Claude CLI",
                "choiceHint": "Reuse a local Claude CLI login on this host",
                "assistantPriority": -20,
                "groupId": "anthropic",
                "groupLabel": "Anthropic",
                "groupHint": "Claude CLI + API key",
                "modelAllowlist": {
                    "allowedKeys": list(_CLAUDE_CLI_CANONICAL_ALLOWLIST_REFS),
                    "initialSelections": [_CLAUDE_CLI_CANONICAL_DEFAULT_MODEL_REF],
                    "message": "Claude CLI models",
                },
            },
            "run": _run_anthropic_cli_migration,
            "runNonInteractive": _run_anthropic_cli_migration_non_interactive,
        },
        {
            "id": "setup-token",
            "label": "Anthropic setup-token",
            "hint": "Manual bearer token path",
            "kind": "token",
            "wizard": {
                "choiceId": "setup-token",
                "choiceLabel": "Anthropic setup-token",
                "choiceHint": "Manual token path",
                "assistantPriority": 40,
                "groupId": "anthropic",
                "groupLabel": "Anthropic",
                "groupHint": "Claude CLI + API key + token",
            },
            "run": _run_anthropic_setup_token_auth,
            "runNonInteractive": _run_anthropic_setup_token_non_interactive,
        },
        create_provider_api_key_auth_method({
            "providerId": provider_id,
            "methodId": "api-key",
            "label": "Anthropic API key",
            "hint": "Direct Anthropic API key",
            "optionKey": "anthropicApiKey",
            "flagName": "--anthropic-api-key",
            "envVar": "ANTHROPIC_API_KEY",
            "promptMessage": "Enter Anthropic API key",
            "defaultModel": default_anthropic_model,
            "expectedProviders": ["anthropic"],
            "wizard": {
                "choiceId": "apiKey",
                "choiceLabel": "Anthropic API key",
                "groupId": "anthropic",
                "groupLabel": "Anthropic",
                "groupHint": "Claude CLI + API key",
            },
        }),
    ]

    provider: dict[str, Any] = {
        "id": provider_id,
        "label": "Anthropic",
        "docsPath": "/providers/models",
        "hookAliases": [CLAUDE_CLI_BACKEND_ID],
        "envVars": ["ANTHROPIC_OAUTH_TOKEN", "ANTHROPIC_API_KEY"],
        "oauthProfileIdRepairs": [
            {
                "legacyProfileId": "anthropic:default",
                "promptLabel": "Anthropic",
            },
        ],
        "auth": auth_methods,
        "normalizeConfig": lambda params: normalize_anthropic_provider_config_for_provider(params),
        "applyConfigDefaults": lambda params: apply_anthropic_config_defaults(params),
        "resolveSyntheticAuth": lambda params: (
            _resolve_claude_cli_synthetic_auth()
            if normalize_lowercase_string_or_empty(params.get("provider", "")) == CLAUDE_CLI_BACKEND_ID
            else None
        ),
        "augmentModelCatalog": lambda _ctx: build_claude_cli_catalog_entries(),
        "resolveReasoningOutputMode": lambda: "native",
        "wrapStreamFn": wrap_anthropic_provider_stream,
        "resolveUsageAuth": _resolve_anthropic_usage_auth,
        "isCacheTtlEligible": lambda: True,
    }

    try:
        from openclaw.plugin_sdk.provider_model_shared import (
            NATIVE_ANTHROPIC_REPLAY_HOOKS,
            resolve_claude_fable5_model_identity,
            resolve_claude_model_identity,
            resolve_claude_thinking_profile,
            supports_claude_adaptive_thinking,
            supports_claude_native_max_effort,
            supports_claude_native_xhigh_effort,
        )

        def _resolve_dynamic_model(ctx: dict[str, Any]) -> dict[str, Any] | None:
            model = _resolve_anthropic_forward_compat_model(ctx)
            if not model:
                return None
            normalized = _normalize_anthropic_resolved_model({
                "config": ctx.get("config"),
                "provider": ctx.get("provider"),
                "modelId": ctx.get("modelId"),
                "model": model,
            })
            return normalized or model

        def _resolve_thinking_profile(params: dict[str, Any]) -> dict[str, Any] | None:
            model_id = params.get("modelId", "")
            model_params = params.get("params")
            contract_model_id = resolve_claude_model_identity({"id": model_id, "params": model_params})
            provider = params.get("provider", "")
            normalized_provider = normalize_lowercase_string_or_empty(provider)
            is_fable5 = resolve_claude_fable5_model_identity({"id": contract_model_id}) is not None
            if is_fable5 and normalized_provider != PROVIDER_ID:
                return CLAUDE_CLI_OFF_THINKING_PROFILE
            return resolve_claude_thinking_profile(
                contract_model_id,
                None,
                includeNativeMax=normalized_provider in (PROVIDER_ID, CLAUDE_CLI_BACKEND_ID),
            )

        def _is_modern_model_ref(params: dict[str, Any]) -> bool:
            model_id = params.get("modelId", "")
            provider = params.get("provider", "")
            normalized_provider = normalize_lowercase_string_or_empty(provider)
            is_fable5 = resolve_claude_fable5_model_identity({"id": model_id}) is not None
            return supports_claude_adaptive_thinking({"id": model_id}) and (
                not is_fable5 or normalized_provider == PROVIDER_ID
            )

        provider["resolveDynamicModel"] = _resolve_dynamic_model
        provider["normalizeResolvedModel"] = _normalize_anthropic_resolved_model
        provider["resolveThinkingProfile"] = _resolve_thinking_profile
        provider["isModernModelRef"] = _is_modern_model_ref
        provider.update(NATIVE_ANTHROPIC_REPLAY_HOOKS)
    except ImportError:
        pass

    return provider


def register_anthropic_plugin(api: OpenClawPluginApi) -> None:
    api.register_cli_backend(build_anthropic_cli_backend())
    api.register_provider(build_anthropic_provider())
    api.register_media_understanding_provider(anthropic_media_understanding_provider)