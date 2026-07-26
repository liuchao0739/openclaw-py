"""Capability-scoped media generation model reference resolution."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TypedDict, TypeVar

from openclaw.packages.normalization_core import normalize_optional_string

from .model_ref import ParsedGenerationModelRef

__all__ = [
    "CapabilityModelProviderCandidate",
    "CapabilityModelRef",
    "find_capability_provider_by_id",
    "resolve_capability_model_ref_for_providers",
    "resolve_capability_provider_model_only_ref",
]

T = TypeVar("T", bound="CapabilityModelProviderCandidate")
ProviderIdNormalizer = Callable[[str], str | None]


class CapabilityModelProviderCandidate(TypedDict, total=False):
    id: str
    aliases: list[str]
    default_model: str | None
    models: list[str]


class CapabilityModelRef(TypedDict):
    provider: str
    model: str


def _normalize_provider_for_match(
    value: str | None,
    normalize_provider_id: ProviderIdNormalizer | None,
) -> str | None:
    normalized = normalize_optional_string(value)
    if normalized and normalize_provider_id:
        return normalize_provider_id(normalized)
    return normalized


def find_capability_provider_by_id(
    *,
    providers: Sequence[T],
    provider_id: str | None = None,
    normalize_provider_id: ProviderIdNormalizer | None = None,
) -> T | None:
    """Find a provider by id or alias using the caller's provider-id normalization rules."""
    selected_provider = _normalize_provider_for_match(provider_id, normalize_provider_id)
    if not selected_provider:
        return None
    for provider in providers:
        candidate_id = _normalize_provider_for_match(provider["id"], normalize_provider_id)
        if candidate_id == selected_provider:
            return provider
        for alias in provider.get("aliases") or []:
            if _normalize_provider_for_match(alias, normalize_provider_id) == selected_provider:
                return provider
    return None


def resolve_capability_provider_model_only_ref(
    *,
    providers: Sequence[CapabilityModelProviderCandidate],
    raw: str | None = None,
) -> CapabilityModelRef | None:
    """Resolve a bare model name to the provider that advertises it for this capability."""
    model = normalize_optional_string(raw)
    if not model:
        return None
    for candidate in providers:
        models = [candidate.get("default_model"), *(candidate.get("models") or [])]
        if any(normalize_optional_string(entry) == model for entry in models):
            return {"provider": candidate["id"], "model": model}
    return None


def resolve_capability_model_ref_for_providers(
    *,
    providers: Sequence[CapabilityModelProviderCandidate],
    raw: str | None = None,
    parse_model_ref: Callable[[str | None], ParsedGenerationModelRef | CapabilityModelRef | None],
    normalize_provider_id: ProviderIdNormalizer | None = None,
) -> CapabilityModelRef | None:
    """Resolve provider/model refs first, then fall back to model-only catalog matching."""
    normalized_raw = normalize_optional_string(raw)
    if not normalized_raw:
        return None
    parsed = parse_model_ref(normalized_raw)
    if parsed and find_capability_provider_by_id(
        providers=providers,
        provider_id=parsed["provider"],
        normalize_provider_id=normalize_provider_id,
    ):
        return parsed
    return resolve_capability_provider_model_only_ref(providers=providers, raw=normalized_raw) or parsed
