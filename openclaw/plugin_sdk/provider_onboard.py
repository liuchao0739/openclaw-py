"""Provider onboarding helpers for bundled provider plugins."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from typing import Any

from openclaw.packages.normalization_core import (
    is_record,
    resolve_primary_string_value,
)

OpenClawConfig = dict[str, Any]
ModelDefinitionConfig = dict[str, Any]
ModelProviderConfig = dict[str, Any]
AgentModelAliasEntry = str | dict[str, Any]

__all__ = [
    "ModelDefinitionConfig",
    "ModelProviderConfig",
    "OpenClawConfig",
    "apply_agent_default_model_primary",
    "apply_onboard_auth_agent_models_and_providers",
    "apply_provider_config_with_default_models",
    "apply_provider_config_with_default_models_preset",
    "apply_provider_config_with_model_catalog",
    "apply_provider_config_with_model_catalog_preset",
    "create_default_models_preset_appliers",
    "create_model_catalog_preset_appliers",
    "resolve_agent_model_fallback_values",
    "resolve_agent_model_primary_value",
    "with_agent_model_aliases",
]


def resolve_agent_model_primary_value(model: Any) -> str | None:
    """Return the primary model ref from either string or object-style agent model config."""
    return resolve_primary_string_value(model)


def resolve_agent_model_fallback_values(model: Any) -> list[str]:
    """Return configured fallback model refs, preserving their configured order."""
    if not is_record(model):
        return []
    fallbacks = model.get("fallbacks")
    return [str(value) for value in fallbacks] if isinstance(fallbacks, list) else []


def _normalize_provider_id(provider: str) -> str:
    return provider.strip().lower()


def _find_normalized_provider_key(
    providers: dict[str, Any] | None,
    provider_id: str,
) -> str | None:
    if not providers:
        return None
    provider_key = _normalize_provider_id(provider_id)
    for key in providers:
        if _normalize_provider_id(key) == provider_key:
            return key
    return None


def normalize_agent_model_ref_for_config(model: str) -> str:
    """Canonicalize provider/model refs before they are persisted to config."""
    trimmed = model.strip()
    slash = trimmed.find("/")
    if slash <= 0 or slash >= len(trimmed) - 1:
        return trimmed
    provider = _normalize_provider_id(trimmed[:slash])
    model_suffix = trimmed[slash + 1 :]
    return f"{provider}/{model_suffix}"


def normalize_agent_model_map_for_config(models: dict[str, Any]) -> dict[str, Any]:
    """Normalize model map keys and merge entries that collapse to the same canonical ref."""
    mutated = False
    next_models: dict[str, Any] = {}
    for key, entry in models.items():
        normalized_key = normalize_agent_model_ref_for_config(key)
        if normalized_key != key or normalized_key in next_models:
            mutated = True
        existing = next_models.get(normalized_key)
        if is_record(existing) and is_record(entry):
            existing_params = existing.get("params") if is_record(existing.get("params")) else {}
            incoming_params = entry.get("params") if is_record(entry.get("params")) else {}
            merged = {**existing, **entry}
            if existing_params or incoming_params:
                merged["params"] = {**existing_params, **incoming_params}
            next_models[normalized_key] = merged
        else:
            next_models[normalized_key] = entry
    return next_models if mutated else models


def _normalize_provider_model_for_config(
    provider_id: str,
    model: ModelDefinitionConfig,
) -> ModelDefinitionConfig:
    model_id = model.get("id")
    normalized_id = str(model_id) if model_id is not None else ""
    return model if normalized_id == model.get("id") else {**model, "id": normalized_id}


def _normalize_provider_models_for_config(
    provider_id: str,
    models: list[ModelDefinitionConfig],
) -> list[ModelDefinitionConfig]:
    next_models: list[ModelDefinitionConfig] = []
    seen_by_id: dict[str, int] = {}
    mutated = False

    for model in models:
        normalized = _normalize_provider_model_for_config(provider_id, model)
        if normalized is not model:
            mutated = True
        existing_index = seen_by_id.get(normalized["id"])
        if existing_index is not None:
            mutated = True
            next_models[existing_index] = {**normalized, **next_models[existing_index]}
            continue
        seen_by_id[normalized["id"]] = len(next_models)
        next_models.append(normalized)

    return next_models if mutated else models


def _normalize_model_providers_for_config(
    providers: dict[str, ModelProviderConfig] | None,
) -> dict[str, ModelProviderConfig] | None:
    if not providers:
        return providers

    mutated = False
    next_providers: dict[str, ModelProviderConfig] = {}
    for provider_id, provider_config in providers.items():
        models = provider_config.get("models")
        if isinstance(models, list):
            normalized_models = _normalize_provider_models_for_config(provider_id, models)
            if normalized_models is not models:
                mutated = True
                next_providers[provider_id] = {**provider_config, "models": normalized_models}
                continue
        next_providers[provider_id] = provider_config
    return next_providers if mutated else providers


def _normalize_agent_model_alias_entry(entry: AgentModelAliasEntry) -> dict[str, Any]:
    if isinstance(entry, str):
        return {"modelRef": entry}
    return entry


def with_agent_model_aliases(
    existing: dict[str, Any] | None,
    aliases: list[AgentModelAliasEntry],
) -> dict[str, Any]:
    """Merge provider alias entries into the agent default model map without clobbering aliases."""
    next_models = normalize_agent_model_map_for_config({**(existing or {})})
    for entry in aliases:
        normalized = _normalize_agent_model_alias_entry(entry)
        model_ref = normalize_agent_model_ref_for_config(normalized["modelRef"])
        alias = normalized.get("alias")
        current = next_models.get(model_ref, {})
        next_entry = dict(current) if is_record(current) else {}
        if alias:
            next_entry["alias"] = next_entry.get("alias") or alias
        next_models[model_ref] = next_entry
    return next_models


def apply_onboard_auth_agent_models_and_providers(
    cfg: OpenClawConfig,
    *,
    agent_models: dict[str, Any],
    providers: dict[str, ModelProviderConfig],
) -> OpenClawConfig:
    """Write onboarding-auth model aliases and provider configs into canonical config sections."""
    merged_agent_models = normalize_agent_model_map_for_config(
        {**(cfg.get("agents", {}).get("defaults", {}).get("models") or {}), **agent_models}
    )
    next_cfg = deepcopy(cfg)
    agents = next_cfg.setdefault("agents", {})
    defaults = agents.setdefault("defaults", {})
    defaults["models"] = merged_agent_models
    models = next_cfg.setdefault("models", {})
    models["mode"] = models.get("mode") or "merge"
    models["providers"] = providers
    return next_cfg


def _has_agent_default_model_primary(cfg: OpenClawConfig) -> bool:
    return (
        resolve_primary_string_value(cfg.get("agents", {}).get("defaults", {}).get("model"))
        is not None
    )


def apply_agent_default_model_primary(cfg: OpenClawConfig, primary: str) -> OpenClawConfig:
    """Set the agent default primary model while preserving normalized fallbacks."""
    next_cfg = deepcopy(cfg)
    defaults = next_cfg.setdefault("agents", {}).setdefault("defaults", {})
    existing_model = defaults.get("model")
    existing_fallbacks = resolve_agent_model_fallback_values(existing_model)
    normalized_fallbacks = [
        normalize_agent_model_ref_for_config(fallback) for fallback in existing_fallbacks
    ]
    model_value: dict[str, Any] = {
        "primary": normalize_agent_model_ref_for_config(primary),
    }
    if normalized_fallbacks:
        model_value["fallbacks"] = normalized_fallbacks
    defaults["model"] = model_value
    if defaults.get("models") is not None:
        defaults["models"] = normalize_agent_model_map_for_config(defaults["models"])
    providers = _normalize_model_providers_for_config(next_cfg.get("models", {}).get("providers"))
    if providers is not None:
        next_cfg.setdefault("models", {})["providers"] = providers
    return next_cfg


def _resolve_provider_model_merge_state(
    cfg: OpenClawConfig,
    provider_id: str,
) -> dict[str, Any]:
    providers = dict(cfg.get("models", {}).get("providers") or {})
    existing_provider_key = _find_normalized_provider_key(providers, provider_id)
    existing_provider = (
        dict(providers[existing_provider_key]) if existing_provider_key is not None else None
    )
    existing_models: list[ModelDefinitionConfig] = []
    if existing_provider and isinstance(existing_provider.get("models"), list):
        existing_models = _normalize_provider_models_for_config(
            provider_id,
            existing_provider["models"],
        )
    if existing_provider_key and existing_provider_key != provider_id:
        providers.pop(existing_provider_key, None)
    if existing_provider is not None:
        existing_provider = {**existing_provider, "models": existing_models}
    return {
        "providers": providers,
        "existing_provider": existing_provider,
        "existing_models": existing_models,
    }


def _build_provider_config(
    *,
    existing_provider: ModelProviderConfig | None,
    api: str,
    base_url: str,
    merged_models: list[ModelDefinitionConfig],
    fallback_models: list[ModelDefinitionConfig],
) -> ModelProviderConfig:
    existing_provider_rest = dict(existing_provider or {})
    existing_api_key = existing_provider_rest.pop("apiKey", None)
    normalized_api_key = existing_api_key.strip() if isinstance(existing_api_key, str) else None
    result: ModelProviderConfig = {
        **existing_provider_rest,
        "baseUrl": base_url,
        "api": api,
        "models": merged_models if merged_models else fallback_models,
    }
    if normalized_api_key:
        result["apiKey"] = normalized_api_key
    return result


def _apply_provider_config_with_merged_models(
    cfg: OpenClawConfig,
    *,
    agent_models: dict[str, Any],
    provider_id: str,
    provider_state: dict[str, Any],
    api: str,
    base_url: str,
    merged_models: list[ModelDefinitionConfig],
    fallback_models: list[ModelDefinitionConfig],
) -> OpenClawConfig:
    merged = _normalize_provider_models_for_config(provider_id, merged_models)
    fallback = _normalize_provider_models_for_config(provider_id, fallback_models)
    providers = provider_state["providers"]
    providers[provider_id] = _build_provider_config(
        existing_provider=provider_state.get("existing_provider"),
        api=api,
        base_url=base_url,
        merged_models=merged,
        fallback_models=fallback,
    )
    return apply_onboard_auth_agent_models_and_providers(
        cfg,
        agent_models=agent_models,
        providers=providers,
    )


def apply_provider_config_with_default_models(
    cfg: OpenClawConfig,
    *,
    agent_models: dict[str, Any],
    provider_id: str,
    api: str,
    base_url: str,
    default_models: list[ModelDefinitionConfig],
    default_model_id: str | None = None,
) -> OpenClawConfig:
    """Merge a provider config with default models using default-model merge semantics."""
    provider_state = _resolve_provider_model_merge_state(cfg, provider_id)
    existing_models = provider_state["existing_models"]
    resolved_default_model_id = default_model_id or (
        default_models[0].get("id") if default_models else None
    )
    has_default_model = (
        any(model.get("id") == resolved_default_model_id for model in existing_models)
        if resolved_default_model_id
        else True
    )
    if existing_models:
        merged_models = (
            existing_models
            if has_default_model or not default_models
            else [*existing_models, *default_models]
        )
    else:
        merged_models = default_models
    return _apply_provider_config_with_merged_models(
        cfg,
        agent_models=agent_models,
        provider_id=provider_id,
        provider_state=provider_state,
        api=api,
        base_url=base_url,
        merged_models=merged_models,
        fallback_models=default_models,
    )


def apply_provider_config_with_default_models_preset(
    cfg: OpenClawConfig,
    *,
    provider_id: str,
    api: str,
    base_url: str,
    default_models: list[ModelDefinitionConfig],
    default_model_id: str | None = None,
    aliases: list[AgentModelAliasEntry] | None = None,
    primary_model_ref: str | None = None,
) -> OpenClawConfig:
    """Apply a default-models provider preset and set primary only when the user has none."""
    defaults_models = cfg.get("agents", {}).get("defaults", {}).get("models")
    next_cfg = apply_provider_config_with_default_models(
        cfg,
        agent_models=with_agent_model_aliases(
            defaults_models if is_record(defaults_models) else None,
            aliases or [],
        ),
        provider_id=provider_id,
        api=api,
        base_url=base_url,
        default_models=default_models,
        default_model_id=default_model_id,
    )
    if primary_model_ref and not _has_agent_default_model_primary(cfg):
        return apply_agent_default_model_primary(next_cfg, primary_model_ref)
    return next_cfg


def apply_provider_config_with_model_catalog(
    cfg: OpenClawConfig,
    *,
    agent_models: dict[str, Any],
    provider_id: str,
    api: str,
    base_url: str,
    catalog_models: list[ModelDefinitionConfig],
) -> OpenClawConfig:
    """Merge a provider config with a catalog while preserving existing model entries first."""
    provider_state = _resolve_provider_model_merge_state(cfg, provider_id)
    existing_models = provider_state["existing_models"]
    if existing_models:
        merged_models = [
            *existing_models,
            *[
                model
                for model in catalog_models
                if not any(existing.get("id") == model.get("id") for existing in existing_models)
            ],
        ]
    else:
        merged_models = catalog_models
    return _apply_provider_config_with_merged_models(
        cfg,
        agent_models=agent_models,
        provider_id=provider_id,
        provider_state=provider_state,
        api=api,
        base_url=base_url,
        merged_models=merged_models,
        fallback_models=catalog_models,
    )


def apply_provider_config_with_model_catalog_preset(
    cfg: OpenClawConfig,
    *,
    provider_id: str,
    api: str,
    base_url: str,
    catalog_models: list[ModelDefinitionConfig],
    aliases: list[AgentModelAliasEntry] | None = None,
    primary_model_ref: str | None = None,
) -> OpenClawConfig:
    """Apply a catalog-backed provider preset and set primary only when the user has none."""
    defaults_models = cfg.get("agents", {}).get("defaults", {}).get("models")
    next_cfg = apply_provider_config_with_model_catalog(
        cfg,
        agent_models=with_agent_model_aliases(
            defaults_models if is_record(defaults_models) else None,
            aliases or [],
        ),
        provider_id=provider_id,
        api=api,
        base_url=base_url,
        catalog_models=catalog_models,
    )
    if primary_model_ref and not _has_agent_default_model_primary(cfg):
        return apply_agent_default_model_primary(next_cfg, primary_model_ref)
    return next_cfg


def create_default_models_preset_appliers(
    *,
    resolve_params: Callable[..., dict[str, Any] | None],
    primary_model_ref: str,
) -> dict[str, Callable[..., OpenClawConfig]]:
    """Build setup appliers for presets that resolve to multiple default provider models."""

    def apply_provider_config(cfg: OpenClawConfig, *args: Any) -> OpenClawConfig:
        resolved = resolve_params(cfg, *args)
        if not resolved:
            return cfg
        return apply_provider_config_with_default_models_preset(cfg, **resolved)

    def apply_config(cfg: OpenClawConfig, *args: Any) -> OpenClawConfig:
        resolved = resolve_params(cfg, *args)
        if not resolved:
            return cfg
        return apply_provider_config_with_default_models_preset(
            cfg,
            **resolved,
            primary_model_ref=primary_model_ref,
        )

    return {
        "applyProviderConfig": apply_provider_config,
        "applyConfig": apply_config,
        "apply_provider_config": apply_provider_config,
        "apply_config": apply_config,
    }


def create_model_catalog_preset_appliers(
    *,
    resolve_params: Callable[..., dict[str, Any] | None],
    primary_model_ref: str,
) -> dict[str, Callable[..., OpenClawConfig]]:
    """Build setup appliers for presets that resolve to a provider model catalog."""

    def apply_provider_config(cfg: OpenClawConfig, *args: Any) -> OpenClawConfig:
        resolved = resolve_params(cfg, *args)
        if not resolved:
            return cfg
        return apply_provider_config_with_model_catalog_preset(cfg, **resolved)

    def apply_config(cfg: OpenClawConfig, *args: Any) -> OpenClawConfig:
        resolved = resolve_params(cfg, *args)
        if not resolved:
            return cfg
        return apply_provider_config_with_model_catalog_preset(
            cfg,
            **resolved,
            primary_model_ref=primary_model_ref,
        )

    return {
        "applyProviderConfig": apply_provider_config,
        "applyConfig": apply_config,
        "apply_provider_config": apply_provider_config,
        "apply_config": apply_config,
    }
