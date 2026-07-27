"""Provider model-id normalization policies from manifests plus built-in provider rules.

Mirrors packages/model-catalog-core/src/provider-model-id-normalization.ts.
"""

from __future__ import annotations

from typing import TypedDict

from openclaw_packages.normalization_core import normalize_lowercase_string_or_empty

from .provider_model_id_normalize import (
    normalize_google_preview_model_id,
    normalize_together_model_id,
)


class PrefixWhenBareAfterAliasStartsWith(TypedDict):
    modelPrefix: str
    prefix: str


class ManifestModelIdNormalizationProvider(TypedDict, total=False):
    aliases: dict[str, str]
    stripPrefixes: list[str]
    prefixWhenBare: str
    prefixWhenBareAfterAliasStartsWith: list[PrefixWhenBareAfterAliasStartsWith]


class ManifestModelIdNormalizationRecord(TypedDict, total=False):
    modelIdNormalization: dict[str, object]


_current_manifest_model_id_normalization_policies: (
    dict[str, ManifestModelIdNormalizationProvider] | None
) = None


def collect_manifest_model_id_normalization_policies(
    plugins: list[ManifestModelIdNormalizationRecord],
) -> dict[str, ManifestModelIdNormalizationProvider]:
    policies: dict[str, ManifestModelIdNormalizationProvider] = {}
    for plugin in plugins:
        normalization = plugin.get("modelIdNormalization")
        if not isinstance(normalization, dict):
            continue
        providers = normalization.get("providers")
        if not isinstance(providers, dict):
            continue
        for provider, policy in providers.items():
            if isinstance(policy, dict):
                policies[normalize_lowercase_string_or_empty(provider)] = policy
    return policies


def set_current_manifest_model_id_normalization_records(
    plugins: list[ManifestModelIdNormalizationRecord] | None,
) -> None:
    global _current_manifest_model_id_normalization_policies
    _current_manifest_model_id_normalization_policies = (
        collect_manifest_model_id_normalization_policies(plugins) if plugins else None
    )


def get_current_manifest_model_id_normalization_policies() -> (
    dict[str, ManifestModelIdNormalizationProvider] | None
):
    return _current_manifest_model_id_normalization_policies


def _has_provider_prefix(model_id: str) -> bool:
    return "/" in model_id


def _format_prefixed_model_id(prefix: str, model_id: str) -> str:
    trimmed_prefix = prefix.rstrip("/")
    trimmed_model = model_id.lstrip("/")
    return f"{trimmed_prefix}/{trimmed_model}"


def strip_self_provider_model_prefix(provider: str, model: str) -> str:
    prefix = f"{normalize_lowercase_string_or_empty(provider)}/"
    trimmed = model.strip()
    if normalize_lowercase_string_or_empty(trimmed).startswith(prefix):
        return trimmed[len(prefix) :]
    return model


def normalize_provider_model_id_with_policies(
    *,
    provider: str,
    policies: dict[str, ManifestModelIdNormalizationProvider],
    context: dict[str, str],
) -> str | None:
    policy = policies.get(normalize_lowercase_string_or_empty(provider))
    if not policy:
        return None

    model_id = context["modelId"].strip()
    if not model_id:
        return model_id

    for prefix in policy.get("stripPrefixes") or []:
        normalized_prefix = normalize_lowercase_string_or_empty(prefix)
        if normalized_prefix and normalize_lowercase_string_or_empty(model_id).startswith(
            normalized_prefix,
        ):
            model_id = model_id[len(normalized_prefix) :]
            break

    aliases = policy.get("aliases") or {}
    model_id = aliases.get(normalize_lowercase_string_or_empty(model_id), model_id)

    if not _has_provider_prefix(model_id):
        for rule in policy.get("prefixWhenBareAfterAliasStartsWith") or []:
            if not isinstance(rule, dict):
                continue
            model_prefix = rule.get("modelPrefix", "")
            rule_prefix = rule.get("prefix", "")
            if normalize_lowercase_string_or_empty(model_id).startswith(
                model_prefix.lower(),
            ):
                return _format_prefixed_model_id(rule_prefix, model_id)
        prefix_when_bare = policy.get("prefixWhenBare")
        if prefix_when_bare:
            return _format_prefixed_model_id(prefix_when_bare, model_id)

    return model_id


def normalize_built_in_provider_model_id(provider: str, model: str) -> str:
    normalized_provider = normalize_lowercase_string_or_empty(provider)
    if normalized_provider in ("google", "google-gemini-cli", "google-vertex"):
        return normalize_google_preview_model_id(model)
    if normalized_provider == "openrouter":
        trimmed = model.strip()
        return f"openrouter/{trimmed}" if trimmed and "/" not in trimmed else model
    if normalized_provider == "anthropic":
        anthropic_aliases = {
            "opus-4.8": "claude-opus-4-8",
            "opus": "claude-opus-4-8",
            "opus-4.6": "claude-opus-4-6",
            "sonnet-4.6": "claude-sonnet-4-6",
        }
        anthropic_prefix = "anthropic/"
        normalized_model = normalize_lowercase_string_or_empty(model)
        provider_model = (
            model.strip()[len(anthropic_prefix) :]
            if normalized_model.startswith(anthropic_prefix)
            else model
        )
        return anthropic_aliases.get(
            normalize_lowercase_string_or_empty(provider_model),
            provider_model,
        )
    if normalized_provider == "vercel-ai-gateway":
        vercel_aliases = {
            "opus-4.6": "claude-opus-4-6",
            "sonnet-4.6": "claude-sonnet-4-6",
        }
        aliased = vercel_aliases.get(normalize_lowercase_string_or_empty(model), model)
        return (
            f"anthropic/{aliased}"
            if normalize_lowercase_string_or_empty(aliased).startswith("claude-")
            else aliased
        )
    if normalized_provider == "huggingface":
        prefix = "huggingface/"
        return model[len(prefix) :] if normalize_lowercase_string_or_empty(model).startswith(
            prefix,
        ) else model
    if normalized_provider == "nvidia":
        trimmed = model.strip()
        return f"nvidia/{trimmed}" if trimmed and "/" not in trimmed else model
    if normalized_provider == "xai":
        xai_aliases = {
            "grok-4-fast-reasoning": "grok-4-fast",
            "grok-4-1-fast-reasoning": "grok-4-1-fast",
            "grok-4.20-experimental-beta-0304-reasoning": "grok-4.20-beta-latest-reasoning",
            "grok-4.20-experimental-beta-0304-non-reasoning": (
                "grok-4.20-beta-latest-non-reasoning"
            ),
            "grok-4.20-reasoning": "grok-4.20-beta-latest-reasoning",
            "grok-4.20-non-reasoning": "grok-4.20-beta-latest-non-reasoning",
        }
        return xai_aliases.get(normalize_lowercase_string_or_empty(model), model)
    if normalized_provider == "openai":
        return model
    if normalized_provider == "together":
        return normalize_together_model_id(model)
    return model


def normalize_static_provider_model_id_with_policies(
    provider: str,
    model: str,
    policies: dict[str, ManifestModelIdNormalizationProvider] | None = None,
) -> str:
    normalized_provider = normalize_lowercase_string_or_empty(provider)
    if policies:
        manifest_model_id = normalize_provider_model_id_with_policies(
            provider=normalized_provider,
            policies=policies,
            context={"modelId": model},
        )
        manifest_model_id = model if manifest_model_id is None else manifest_model_id
    else:
        manifest_model_id = model
    return normalize_built_in_provider_model_id(normalized_provider, manifest_model_id)


def normalize_configured_provider_catalog_model_id(
    provider: str,
    model: str,
    policies: dict[str, ManifestModelIdNormalizationProvider] | None = None,
) -> str:
    if policies is None:
        policies = get_current_manifest_model_id_normalization_policies()
    provider_model = normalize_static_provider_model_id_with_policies(
        provider,
        model,
        policies,
    )
    return normalize_configured_provider_catalog_model_ref(provider_model)


def normalize_configured_provider_catalog_model_ref(provider_model: str) -> str:
    google_prefix = "google/"
    if not provider_model.startswith(google_prefix):
        slash = provider_model.find("/")
        if slash <= 0 or slash >= len(provider_model) - 1:
            return provider_model
        prefix = provider_model[: slash + 1]
        suffix = provider_model[slash + 1 :]
        if not suffix.startswith(google_prefix):
            return provider_model
        normalized_suffix = normalize_google_preview_model_id(suffix)
        return (
            provider_model
            if normalized_suffix == suffix
            else f"{prefix}{normalized_suffix}"
        )
    model_id = provider_model[len(google_prefix) :]
    normalized_model_id = normalize_google_preview_model_id(model_id)
    return (
        provider_model
        if normalized_model_id == model_id
        else f"{google_prefix}{normalized_model_id}"
    )


__all__ = [
    "ManifestModelIdNormalizationProvider",
    "ManifestModelIdNormalizationRecord",
    "collect_manifest_model_id_normalization_policies",
    "get_current_manifest_model_id_normalization_policies",
    "normalize_built_in_provider_model_id",
    "normalize_configured_provider_catalog_model_id",
    "normalize_configured_provider_catalog_model_ref",
    "normalize_provider_model_id_with_policies",
    "normalize_static_provider_model_id_with_policies",
    "set_current_manifest_model_id_normalization_records",
    "strip_self_provider_model_prefix",
]
