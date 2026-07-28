from __future__ import annotations

from typing import Any

from openclaw.packages.normalization_core import (
    is_record,
    normalize_lowercase_string_or_empty,
)

from .claude_model_refs import (
    resolve_claude_cli_anthropic_model_refs,
    resolve_known_anthropic_model_ref,
)
from .cli_constants import (
    CLAUDE_CLI_BACKEND_ID,
    CLAUDE_CLI_DEFAULT_ALLOWLIST_REFS,
)

_ANTHROPIC_PROVIDER_API = "anthropic-messages"
_ANTHROPIC_API_KEY_DEFAULT_ALLOWLIST_REFS = ["anthropic/claude-sonnet-4-6"]


def _normalize_provider_id(provider: str) -> str:
    normalized = normalize_lowercase_string_or_empty(provider)
    if normalized in ("bedrock", "aws-bedrock"):
        return "amazon-bedrock"
    return normalized


def _resolve_anthropic_default_auth_mode(
    config: dict[str, Any],
    env: dict[str, str],
) -> str | None:
    profiles = config.get("auth", {}).get("profiles", {})
    if not isinstance(profiles, dict):
        profiles = {}
    anthropic_profiles = {
        k: v for k, v in profiles.items()
        if isinstance(v, dict)
        and (v.get("provider") == "anthropic" or v.get("provider") == CLAUDE_CLI_BACKEND_ID)
    }

    order = [
        *(config.get("auth", {}).get("order", {}).get("anthropic", []) or []),
        *(
            config.get("auth", {})
            .get("order", {})
            .get(CLAUDE_CLI_BACKEND_ID, []) or []
        ),
    ]
    for profile_id in order:
        entry = profiles.get(profile_id)
        if not entry or (entry.get("provider") not in ("anthropic", CLAUDE_CLI_BACKEND_ID)):
            continue
        if entry.get("provider") == CLAUDE_CLI_BACKEND_ID:
            return "oauth"
        if entry.get("mode") == "api_key":
            return "api_key"
        if entry.get("mode") in ("oauth", "token"):
            return "oauth"

    has_api_key = any(
        p.get("provider") == "anthropic" and p.get("mode") == "api_key"
        for p in anthropic_profiles.values()
    )
    has_oauth = any(
        p.get("provider") == CLAUDE_CLI_BACKEND_ID
        or p.get("mode") in ("oauth", "token")
        for p in anthropic_profiles.values()
    )
    if has_api_key and not has_oauth:
        return "api_key"
    if has_oauth and not has_api_key:
        return "oauth"

    if env.get("ANTHROPIC_OAUTH_TOKEN", "").strip():
        return "oauth"
    if env.get("ANTHROPIC_API_KEY", "").strip():
        return "api_key"
    return None


def _resolve_model_primary_value(
    value: Any,
) -> str | None:
    if isinstance(value, str):
        trimmed = value.strip()
        return trimmed or None
    if isinstance(value, dict):
        primary = value.get("primary")
        if isinstance(primary, str):
            trimmed = primary.strip()
            return trimmed or None
    return None


def _parse_provider_model_ref(
    raw: str, default_provider: str
) -> dict[str, str] | None:
    trimmed = raw.strip()
    if not trimmed:
        return None
    slash_index = trimmed.find("/")
    if slash_index <= 0:
        return {"provider": default_provider, "model": trimmed}
    provider = trimmed[:slash_index].strip()
    model = trimmed[slash_index + 1:].strip()
    if not provider or not model:
        return None
    return {
        "provider": _normalize_provider_id(provider),
        "model": model,
    }


def _is_anthropic_cache_retention_target(
    parsed: dict[str, str] | None,
) -> bool:
    return bool(
        parsed
        and (
            parsed["provider"] == "anthropic"
            or (
                parsed["provider"] == "amazon-bedrock"
                and normalize_lowercase_string_or_empty(parsed["model"]).startswith(
                    "anthropic.claude"
                )
            )
        )
    )


def _uses_claude_cli_model_selection(config: dict[str, Any]) -> bool:
    defaults = config.get("agents", {}).get("defaults", {})
    primary = _resolve_model_primary_value(
        defaults.get("model") if isinstance(defaults, dict) else None
    )
    parsed_primary = _parse_provider_model_ref(primary, "anthropic") if primary else None
    if parsed_primary and parsed_primary["provider"] == CLAUDE_CLI_BACKEND_ID:
        return True
    models = defaults.get("models", {}) if isinstance(defaults, dict) else {}
    if isinstance(models, dict):
        for key, entry in models.items():
            parsed = _parse_provider_model_ref(key, "anthropic")
            if parsed and parsed["provider"] == CLAUDE_CLI_BACKEND_ID:
                return True
            agent_runtime = entry.get("agentRuntime") if isinstance(entry, dict) else None
            if is_record(agent_runtime):
                runtime_id = agent_runtime.get("id")
                if normalize_lowercase_string_or_empty(runtime_id) == CLAUDE_CLI_BACKEND_ID:
                    return True
    return False


def _uses_selected_claude_cli_auth_profile(config: dict[str, Any]) -> bool:
    profiles = config.get("auth", {}).get("profiles", {})
    if not isinstance(profiles, dict):
        profiles = {}
    ordered_profile_ids = [
        *(config.get("auth", {}).get("order", {}).get("anthropic", []) or []),
        *(
            config.get("auth", {})
            .get("order", {})
            .get(CLAUDE_CLI_BACKEND_ID, []) or []
        ),
    ]
    for profile_id in ordered_profile_ids:
        provider = profiles.get(profile_id, {}).get("provider")
        if provider == CLAUDE_CLI_BACKEND_ID:
            return True
        if provider == "anthropic":
            return False

    has_claude_cli_profile = False
    has_anthropic_profile = False
    for profile in profiles.values():
        if isinstance(profile, dict):
            if profile.get("provider") == CLAUDE_CLI_BACKEND_ID:
                has_claude_cli_profile = True
            if profile.get("provider") == "anthropic":
                has_anthropic_profile = True
    return has_claude_cli_profile and not has_anthropic_profile


def _to_canonical_anthropic_model_ref(ref: str) -> str:
    if ref.startswith(f"{CLAUDE_CLI_BACKEND_ID}/"):
        return f"anthropic/{ref[len(CLAUDE_CLI_BACKEND_ID) + 1:]}"
    return ref


def _model_entry_with_claude_cli_runtime(entry: Any) -> dict[str, Any]:
    base: dict[str, Any] = dict(entry) if is_record(entry) else {}
    current_runtime_id = base.get("agentRuntime", {}).get("id") if is_record(base.get("agentRuntime")) else None
    current_runtime = normalize_lowercase_string_or_empty(current_runtime_id)
    if current_runtime and current_runtime != "auto":
        return base
    agent_runtime = base.get("agentRuntime", {})
    if not is_record(agent_runtime):
        agent_runtime = {}
    agent_runtime = {
        **agent_runtime,
        "id": CLAUDE_CLI_BACKEND_ID,
    }
    base["agentRuntime"] = agent_runtime
    return base


def _collect_claude_cli_runtime_refs(
    model: Any,
) -> list[str]:
    refs: set[str] = set()
    if isinstance(model, str):
        result = resolve_claude_cli_anthropic_model_refs(model)
        if result:
            for ref in result.get("runtimeRefs", []):
                refs.add(ref)
        return list(refs)
    if isinstance(model, dict):
        primary = model.get("primary")
        if isinstance(primary, str):
            result = resolve_claude_cli_anthropic_model_refs(primary)
            if result:
                for ref in result.get("runtimeRefs", []):
                    refs.add(ref)
        fallbacks = model.get("fallbacks")
        if isinstance(fallbacks, list):
            for fallback in fallbacks:
                if isinstance(fallback, str):
                    result = resolve_claude_cli_anthropic_model_refs(fallback)
                    if result:
                        for ref in result.get("runtimeRefs", []):
                            refs.add(ref)
    return list(refs)


def _collect_claude_cli_runtime_refs_from_model_map(
    models: dict[str, Any] | None,
) -> list[str]:
    refs: set[str] = set()
    if isinstance(models, dict):
        for key in models:
            result = resolve_claude_cli_anthropic_model_refs(key)
            if result:
                for ref in result.get("runtimeRefs", []):
                    refs.add(ref)
    return list(refs)


def _collect_claude_cli_runtime_refs_from_config(config: dict[str, Any]) -> list[str]:
    refs: set[str] = set()
    defaults = config.get("agents", {}).get("defaults", {})
    if isinstance(defaults, dict):
        model = defaults.get("model")
        if model:
            for ref in _collect_claude_cli_runtime_refs(model):
                refs.add(ref)
        models = defaults.get("models")
        for ref in _collect_claude_cli_runtime_refs_from_model_map(models if isinstance(models, dict) else None):
            refs.add(ref)
    agents = config.get("agents", {}).get("list", [])
    if isinstance(agents, list):
        for agent in agents:
            if isinstance(agent, dict):
                model = agent.get("model")
                if model:
                    for ref in _collect_claude_cli_runtime_refs(model):
                        refs.add(ref)
                models = agent.get("models")
                for ref in _collect_claude_cli_runtime_refs_from_model_map(models if isinstance(models, dict) else None):
                    refs.add(ref)
    return list(refs)


def _normalize_anthropic_provider_config(
    provider_config: dict[str, Any],
) -> dict[str, Any]:
    if (
        provider_config.get("api")
        or not isinstance(provider_config.get("models"), list)
        or len(provider_config.get("models", [])) == 0
    ):
        return provider_config
    return {**provider_config, "api": _ANTHROPIC_PROVIDER_API}


def normalize_anthropic_provider_config_for_provider(
    params: dict[str, Any],
) -> Any:
    provider = _normalize_provider_id(params.get("provider", ""))
    if provider not in ("anthropic", CLAUDE_CLI_BACKEND_ID):
        return params.get("providerConfig")
    return _normalize_anthropic_provider_config(params.get("providerConfig", {}))


def apply_anthropic_config_defaults(
    params: dict[str, Any],
) -> dict[str, Any]:
    config = params.get("config", {})
    env = params.get("env", {})
    defaults = config.get("agents", {}).get("defaults")
    if not isinstance(defaults, dict):
        return config

    auth_mode = _resolve_anthropic_default_auth_mode(config, env)
    if not auth_mode:
        return config

    mutated = False
    next_defaults = dict(defaults)
    context_pruning = defaults.get("contextPruning", {})
    heartbeat = defaults.get("heartbeat", {})

    if "mode" not in (context_pruning or {}):
        next_defaults["contextPruning"] = {
            **(context_pruning or {}),
            "mode": "cache-ttl",
            "ttl": (context_pruning or {}).get("ttl", "1h"),
        }
        mutated = True

    if "every" not in (heartbeat or {}):
        next_defaults["heartbeat"] = {
            **(heartbeat or {}),
            "every": "1h" if auth_mode == "oauth" else "30m",
        }
        mutated = True

    if auth_mode == "api_key":
        next_models = dict(defaults.get("models", {}) or {})
        models_mutated = False

        for key, entry in next_models.items():
            parsed = _parse_provider_model_ref(key, "anthropic")
            if not _is_anthropic_cache_retention_target(parsed):
                continue
            current = entry if isinstance(entry, dict) else {}
            params_value = current.get("params", {}) if isinstance(current, dict) else {}
            if isinstance(params_value, dict) and isinstance(params_value.get("cacheRetention"), str):
                continue
            new_entry: dict[str, Any] = dict(current) if isinstance(current, dict) else {}
            params_dict = new_entry.get("params", {})
            if not isinstance(params_dict, dict):
                params_dict = {}
            new_entry["params"] = {**params_dict, "cacheRetention": "short"}
            next_models[key] = new_entry
            models_mutated = True

        primary_ref = resolve_known_anthropic_model_ref(
            _resolve_model_primary_value(defaults.get("model"))
        )
        if primary_ref:
            parsed_primary = _parse_provider_model_ref(primary_ref, "anthropic")
            if parsed_primary and _is_anthropic_cache_retention_target(parsed_primary):
                key = f"{parsed_primary['provider']}/{parsed_primary['model']}"
                entry = next_models.get(key, {})
                current = entry if isinstance(entry, dict) else {}
                params_value = current.get("params", {}) if isinstance(current, dict) else {}
                if not isinstance(params_value, dict) or not isinstance(params_value.get("cacheRetention"), str):
                    new_entry = dict(current) if isinstance(current, dict) else {}
                    params_dict = new_entry.get("params", {})
                    if not isinstance(params_dict, dict):
                        params_dict = {}
                    new_entry["params"] = {**params_dict, "cacheRetention": "short"}
                    next_models[key] = new_entry
                    models_mutated = True

        has_anthropic_api_key_model = any(
            _is_anthropic_cache_retention_target(_parse_provider_model_ref(k, "anthropic"))
            for k in next_models
        )
        if has_anthropic_api_key_model:
            for ref in _ANTHROPIC_API_KEY_DEFAULT_ALLOWLIST_REFS:
                if ref in next_models:
                    continue
                next_models[ref] = {"params": {"cacheRetention": "short"}}
                models_mutated = True

        if models_mutated:
            next_defaults["models"] = next_models
            mutated = True

    if (
        auth_mode == "oauth"
        and (_uses_claude_cli_model_selection(config) or _uses_selected_claude_cli_auth_profile(config))
    ):
        next_models = dict(defaults.get("models", {}) or {})
        models_mutated = False
        runtime_refs: set[str] = set(_collect_claude_cli_runtime_refs_from_config(config))
        for raw_ref in CLAUDE_CLI_DEFAULT_ALLOWLIST_REFS:
            runtime_refs.add(_to_canonical_anthropic_model_ref(raw_ref))
        for ref in runtime_refs:
            current = next_models.get(ref)
            updated = _model_entry_with_claude_cli_runtime(current)
            if isinstance(current, dict) and updated == current:
                continue
            if not isinstance(current, dict) and updated == {}:
                continue
            next_models[ref] = updated
            models_mutated = True
        if models_mutated:
            next_defaults["models"] = next_models
            mutated = True

    if not mutated:
        return config

    return {
        **config,
        "agents": {
            **config.get("agents", {}),
            "defaults": next_defaults,
        },
    }