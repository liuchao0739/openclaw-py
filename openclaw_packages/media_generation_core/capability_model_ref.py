from typing import Any, Callable, List, Optional, Sequence, TypedDict

from .string import normalize_optional_string


class CapabilityModelProviderCandidate(TypedDict, total=False):
    id: str
    aliases: Sequence[str]
    defaultModel: Optional[str]
    models: Sequence[str]


class CapabilityModelRef(TypedDict):
    provider: str
    model: str


ProviderIdNormalizer = Callable[[str], Optional[str]]


def _normalize_provider_for_match(
    value: Optional[str],
    normalize_provider_id: Optional[ProviderIdNormalizer],
) -> Optional[str]:
    normalized = normalize_optional_string(value)
    if normalized and normalize_provider_id:
        return normalize_provider_id(normalized)
    return normalized


def find_capability_provider_by_id(
    providers: Sequence[CapabilityModelProviderCandidate],
    provider_id: Optional[str] = None,
    normalize_provider_id: Optional[ProviderIdNormalizer] = None,
) -> Optional[CapabilityModelProviderCandidate]:
    selected_provider = _normalize_provider_for_match(provider_id, normalize_provider_id)
    if not selected_provider:
        return None
    for provider in providers:
        provider_id_norm = _normalize_provider_for_match(provider.get("id"), normalize_provider_id)
        if provider_id_norm == selected_provider:
            return provider
        aliases = provider.get("aliases") or []
        for alias in aliases:
            alias_norm = _normalize_provider_for_match(alias, normalize_provider_id)
            if alias_norm == selected_provider:
                return provider
    return None


def resolve_capability_provider_model_only_ref(
    providers: Sequence[CapabilityModelProviderCandidate],
    raw: Optional[str] = None,
) -> Optional[CapabilityModelRef]:
    model = normalize_optional_string(raw)
    if not model:
        return None
    for candidate in providers:
        default_model = candidate.get("defaultModel")
        models = list(candidate.get("models") or [])
        candidates = [default_model, *models]
        for entry in candidates:
            if normalize_optional_string(entry) == model:
                return {"provider": candidate["id"], "model": model}
    return None


def resolve_capability_model_ref_for_providers(
    providers: Sequence[CapabilityModelProviderCandidate],
    raw: Optional[str],
    parse_model_ref: Callable[[Optional[str]], Optional[CapabilityModelRef]],
    normalize_provider_id: Optional[ProviderIdNormalizer] = None,
) -> Optional[CapabilityModelRef]:
    raw_norm = normalize_optional_string(raw)
    if not raw_norm:
        return None
    parsed = parse_model_ref(raw_norm)
    if parsed and find_capability_provider_by_id(
        providers=providers,
        provider_id=parsed["provider"],
        normalize_provider_id=normalize_provider_id,
    ):
        return parsed
    return resolve_capability_provider_model_only_ref(providers=providers, raw=raw_norm) or parsed
