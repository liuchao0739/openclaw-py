import re
from typing import Any, Dict, List, Optional, Sequence, TypedDict

from .provider_id import normalize_lowercase_string_or_empty
from .provider_model_id_normalize import (
    normalize_google_preview_model_id,
    normalize_together_model_id,
)


class ManifestModelIdNormalizationPrefixWhenBareAfterAlias(TypedDict):
    modelPrefix: str
    prefix: str


class ManifestModelIdNormalizationProvider(TypedDict, total=False):
    aliases: Dict[str, str]
    stripPrefixes: List[str]
    prefixWhenBare: str
    prefixWhenBareAfterAliasStartsWith: List[ManifestModelIdNormalizationPrefixWhenBareAfterAlias]


class ManifestModelIdNormalizationRecord(TypedDict, total=False):
    modelIdNormalization: Optional[dict]


_current_manifest_model_id_normalization_policies: Optional[Dict[str, ManifestModelIdNormalizationProvider]] = None


def collect_manifest_model_id_normalization_policies(
    plugins: Sequence[ManifestModelIdNormalizationRecord],
) -> Dict[str, ManifestModelIdNormalizationProvider]:
    policies: Dict[str, ManifestModelIdNormalizationProvider] = {}
    for plugin in plugins:
        providers = (plugin.get("modelIdNormalization") or {}).get("providers") or {}
        for provider, policy in providers.items():
            policies[normalize_lowercase_string_or_empty(provider)] = policy
    return policies


def set_current_manifest_model_id_normalization_records(
    plugins: Optional[Sequence[ManifestModelIdNormalizationRecord]],
) -> None:
    global _current_manifest_model_id_normalization_policies
    if plugins is None:
        _current_manifest_model_id_normalization_policies = None
    else:
        _current_manifest_model_id_normalization_policies = collect_manifest_model_id_normalization_policies(plugins)


def get_current_manifest_model_id_normalization_policies() -> Optional[Dict[str, ManifestModelIdNormalizationProvider]]:
    return _current_manifest_model_id_normalization_policies


def _has_provider_prefix(model_id: str) -> bool:
    return "/" in model_id


def _format_prefixed_model_id(prefix: str, model_id: str) -> str:
    prefix = re.sub(r"/+$", "", prefix)
    model_id = re.sub(r"^/+", "", model_id)
    return f"{prefix}/{model_id}"


def strip_self_provider_model_prefix(provider: str, model: str) -> str:
    prefix = f"{normalize_lowercase_string_or_empty(provider)}/"
    trimmed = model.strip()
    if normalize_lowercase_string_or_empty(trimmed).startswith(prefix):
        return trimmed[len(prefix):]
    return model


def normalize_provider_model_id_with_policies(params: dict) -> Optional[str]:
    provider = normalize_lowercase_string_or_empty(params["provider"])
    policies = params["policies"]
    policy = policies.get(provider)
    if policy is None:
        return None

    model_id = params["context"]["modelId"].strip()
    if not model_id:
        return model_id

    strip_prefixes = policy.get("stripPrefixes") or []
    for prefix in strip_prefixes:
        normalized_prefix = normalize_lowercase_string_or_empty(prefix)
        if normalized_prefix and normalize_lowercase_string_or_empty(model_id).startswith(normalized_prefix):
            model_id = model_id[len(normalized_prefix):]
            break

    aliases = policy.get("aliases") or {}
    model_id = aliases.get(normalize_lowercase_string_or_empty(model_id), model_id)

    if not _has_provider_prefix(model_id):
        prefix_rules = policy.get("prefixWhenBareAfterAliasStartsWith") or []
        for rule in prefix_rules:
            if normalize_lowercase_string_or_empty(model_id).startswith(rule["modelPrefix"].lower()):
                return _format_prefixed_model_id(rule["prefix"], model_id)
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
        if trimmed and "/" not in trimmed:
            return f"openrouter/{trimmed}"
        return model
    if normalized_provider == "anthropic":
        anthropic_aliases = {
            "opus-4.8": "claude-opus-4-8",
            "opus": "claude-opus-4-8",
            "opus-4.6": "claude-opus-4-6",
            "sonnet-4.6": "claude-sonnet-4-6",
        }
        anthropic_prefix = "anthropic/"
        normalized_model = normalize_lowercase_string_or_empty(model)
        if normalized_model.startswith(anthropic_prefix):
            provider_model = model.strip()[len(anthropic_prefix):]
        else:
            provider_model = model
        return anthropic_aliases.get(normalize_lowercase_string_or_empty(provider_model), provider_model)
    if normalized_provider == "vercel-ai-gateway":
        vercel_aliases = {
            "opus-4.6": "claude-opus-4-6",
            "sonnet-4.6": "claude-sonnet-4-6",
        }
        aliased = vercel_aliases.get(normalize_lowercase_string_or_empty(model), model)
        if normalize_lowercase_string_or_empty(aliased).startswith("claude-"):
            return f"anthropic/{aliased}"
        return aliased
    if normalized_provider == "huggingface":
        prefix = "huggingface/"
        if normalize_lowercase_string_or_empty(model).startswith(prefix):
            return model[len(prefix):]
        return model
    if normalized_provider == "nvidia":
        trimmed = model.strip()
        if trimmed and "/" not in trimmed:
            return f"nvidia/{trimmed}"
        return model
    if normalized_provider == "xai":
        xai_aliases = {
            "grok-4-fast-reasoning": "grok-4-fast",
            "grok-4-1-fast-reasoning": "grok-4-1-fast",
            "grok-4.20-experimental-beta-0304-reasoning": "grok-4.20-beta-latest-reasoning",
            "grok-4.20-experimental-beta-0304-non-reasoning": "grok-4.20-beta-latest-non-reasoning",
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
    policies: Optional[Dict[str, ManifestModelIdNormalizationProvider]] = None,
) -> str:
    normalized_provider = normalize_lowercase_string_or_empty(provider)
    if policies:
        manifest_model_id = normalize_provider_model_id_with_policies({
            "provider": normalized_provider,
            "policies": policies,
            "context": {"modelId": model},
        })
        if manifest_model_id is None:
            manifest_model_id = model
    else:
        manifest_model_id = model
    return normalize_built_in_provider_model_id(normalized_provider, manifest_model_id)


def normalize_configured_provider_catalog_model_id(
    provider: str,
    model: str,
    policies: Optional[Dict[str, ManifestModelIdNormalizationProvider]] = None,
) -> str:
    if policies is None:
        policies = get_current_manifest_model_id_normalization_policies()
    provider_model = normalize_static_provider_model_id_with_policies(provider, model, policies)
    return normalize_configured_provider_catalog_model_ref(provider_model)


def normalize_configured_provider_catalog_model_ref(provider_model: str) -> str:
    google_prefix = "google/"
    if not provider_model.startswith(google_prefix):
        slash = provider_model.find("/")
        if slash <= 0 or slash >= len(provider_model) - 1:
            return provider_model
        prefix = provider_model[:slash + 1]
        suffix = provider_model[slash + 1:]
        if not suffix.startswith(google_prefix):
            return provider_model
        normalized_suffix = normalize_google_preview_model_id(suffix)
        return provider_model if normalized_suffix == suffix else f"{prefix}{normalized_suffix}"
    model_id = provider_model[len(google_prefix):]
    normalized_model_id = normalize_google_preview_model_id(model_id)
    return provider_model if normalized_model_id == model_id else f"{google_prefix}{normalized_model_id}"
