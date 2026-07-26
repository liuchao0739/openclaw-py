"""Voice model catalog helpers shared by TTS and realtime voice plugins.

Mirrors packages/speech-core/voice-models.ts.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any, Literal, TypedDict, TypeVar

from openclaw.packages.normalization_core import (
    normalize_optional_lowercase_string,
    normalize_optional_string,
)

__all__ = [
    "VoiceModelCapabilities",
    "VoiceModelCapability",
    "VoiceModelCatalogEntry",
    "VoiceModelProvider",
    "VoiceModelRef",
    "VoiceProviderCandidate",
    "find_voice_model_provider",
    "get_voice_provider_config",
    "provider_matches_id",
    "resolve_primary_voice_provider_candidate",
    "resolve_supported_voice_model_refs",
    "resolve_voice_model_refs",
    "resolve_voice_provider_candidates",
    "synthesize_voice_model_catalog_entries",
    "voice_provider_supports_model",
]

VoiceModelCapability = Literal["tts", "realtime_transcription", "realtime_voice"]
VoiceModelCapabilities = dict[VoiceModelCapability, Literal[True]]
VoiceModelCatalogSource = Literal["static"]

T = TypeVar("T", bound="VoiceModelProvider")


class VoiceModelRef(TypedDict, total=False):
    provider: str
    model: str
    timeout_ms: int


class VoiceModelProvider(TypedDict, total=False):
    id: str
    aliases: list[str]
    label: str
    default_model: str | None
    models: list[str]


class VoiceModelCatalogEntry(TypedDict, total=False):
    kind: Literal["voice"]
    provider: str
    model: str
    source: VoiceModelCatalogSource
    capabilities: VoiceModelCapabilities
    label: str
    default: bool
    modes: list[str]


class VoiceProviderCandidate(TypedDict, total=False):
    provider: str
    voice_model: VoiceModelRef


def _normalize_timeout_ms(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, float) and math.isfinite(value) and value > 0:
        return math.floor(value)
    return None


def _parse_voice_model_ref(value: Any) -> VoiceModelRef | None:
    raw = normalize_optional_string(value)
    if not raw:
        return None
    slash_index = raw.find("/")
    if slash_index <= 0 or slash_index == len(raw) - 1:
        return None
    provider = normalize_optional_lowercase_string(raw[:slash_index])
    model = normalize_optional_string(raw[slash_index + 1 :])
    if provider and model:
        return {"provider": provider, "model": model}
    return None


def _same_provider(left: str | None, right: str | None) -> bool:
    normalized_left = normalize_optional_lowercase_string(left)
    return bool(normalized_left and normalized_left == normalize_optional_lowercase_string(right))


def provider_matches_id(provider: VoiceModelProvider, provider_id: str | None = None) -> bool:
    """Match provider ids case-insensitively across canonical id and aliases."""
    if _same_provider(provider["id"], provider_id):
        return True
    return any(_same_provider(alias, provider_id) for alias in provider.get("aliases") or [])


def find_voice_model_provider(
    *,
    providers: Sequence[T],
    provider_id: str | None = None,
) -> T | None:
    """Find the provider metadata for a configured provider id or alias."""
    for provider in providers:
        if provider_matches_id(provider, provider_id):
            return provider
    return None


def voice_provider_supports_model(
    provider: VoiceModelProvider | None,
    model: Any,
) -> bool:
    """Return true when a provider advertises the requested model."""
    if not provider:
        return False
    normalized_model = normalize_optional_string(model)
    candidates = [provider.get("default_model"), *(provider.get("models") or [])]
    return any(normalize_optional_string(candidate) == normalized_model for candidate in candidates)


def resolve_voice_model_refs(config: Any) -> list[VoiceModelRef]:
    """Parse primary/fallback voice model refs from config."""
    if isinstance(config, str):
        parsed = _parse_voice_model_ref(config)
        return [parsed] if parsed else []

    if not isinstance(config, Mapping):
        return []

    timeout_ms = _normalize_timeout_ms(config.get("timeoutMs"))
    refs: list[VoiceModelRef] = []

    def add_ref(value: Any) -> None:
        parsed = _parse_voice_model_ref(value)
        if not parsed:
            return
        ref: VoiceModelRef = {"provider": parsed["provider"], "model": parsed["model"]}
        if timeout_ms is not None:
            ref["timeout_ms"] = timeout_ms
        refs.append(ref)

    add_ref(config.get("primary"))
    fallbacks = config.get("fallbacks")
    if isinstance(fallbacks, list):
        for fallback in fallbacks:
            add_ref(fallback)
    return refs


def resolve_supported_voice_model_refs(
    *,
    config: Any,
    providers: Sequence[VoiceModelProvider],
    provider_id: str | None = None,
) -> list[VoiceModelRef]:
    """Resolve configured voice model refs that are supported by known providers."""
    supported: list[VoiceModelRef] = []
    for ref in resolve_voice_model_refs(config):
        provider = find_voice_model_provider(providers=providers, provider_id=ref["provider"])
        if not provider or (provider_id and not provider_matches_id(provider, provider_id)):
            continue
        if not voice_provider_supports_model(provider, ref["model"]):
            continue
        supported.append({**ref, "provider": provider["id"]})
    return supported


def resolve_voice_provider_candidates(
    *,
    primary_provider: str,
    providers: Sequence[VoiceModelProvider],
    voice_model_config: Any = None,
) -> list[VoiceProviderCandidate]:
    """Build ordered provider candidates from primary provider plus voice-model fallbacks."""
    matched_primary = find_voice_model_provider(providers=providers, provider_id=primary_provider)
    primary = matched_primary["id"] if matched_primary else primary_provider
    candidates: list[VoiceProviderCandidate] = []
    seen_providers: set[str] = set()

    def add_candidate(candidate: VoiceProviderCandidate) -> None:
        candidates.append(candidate)
        seen_providers.add(candidate["provider"])

    refs = resolve_supported_voice_model_refs(config=voice_model_config, providers=providers)
    primary_refs = [ref for ref in refs if ref["provider"] == primary]
    for voice_model in primary_refs:
        add_candidate({"provider": primary, "voice_model": voice_model})
    if not primary_refs:
        add_candidate({"provider": primary})
    for voice_model in refs:
        if voice_model["provider"] != primary:
            add_candidate({"provider": voice_model["provider"], "voice_model": voice_model})
    for provider in providers:
        if provider["id"] not in seen_providers:
            add_candidate({"provider": provider["id"]})
    return candidates


def resolve_primary_voice_provider_candidate(
    *,
    primary_provider: str,
    providers: Sequence[VoiceModelProvider],
    voice_model_config: Any = None,
) -> VoiceProviderCandidate:
    """Resolve only the primary provider candidate for direct synthesis paths."""
    matched_primary = find_voice_model_provider(providers=providers, provider_id=primary_provider)
    provider = matched_primary["id"] if matched_primary else primary_provider
    voice_models = resolve_supported_voice_model_refs(
        config=voice_model_config,
        providers=providers,
        provider_id=provider,
    )
    if voice_models:
        return {"provider": provider, "voice_model": voice_models[0]}
    return {"provider": provider}


def get_voice_provider_config(
    *,
    provider_configs: Mapping[str, Any],
    provider: VoiceModelProvider,
    configured_provider_id: str | None = None,
) -> dict[str, Any]:
    """Read provider config by configured id, canonical id, or alias."""
    candidates = [
        normalize_optional_string(configured_provider_id),
        provider["id"],
        *(provider.get("aliases") or []),
    ]
    configured_keys = list(provider_configs.keys())
    for candidate in (value for value in candidates if value):
        if candidate in provider_configs:
            value = provider_configs[candidate]
            return dict(value) if isinstance(value, Mapping) else {}
        normalized_candidate = normalize_optional_lowercase_string(candidate)
        matching_key = next(
            (
                key
                for key in configured_keys
                if normalize_optional_lowercase_string(key) == normalized_candidate
            ),
            None,
        )
        if matching_key is not None:
            value = provider_configs[matching_key]
            return dict(value) if isinstance(value, Mapping) else {}
    return {}


def synthesize_voice_model_catalog_entries(
    *,
    provider: VoiceModelProvider,
    capabilities: VoiceModelCapabilities,
    modes: Sequence[str] | None = None,
) -> list[VoiceModelCatalogEntry]:
    """Convert provider metadata into static voice catalog entries."""
    seen: set[str] = set()
    models: list[str] = []
    for entry in [provider.get("default_model"), *(provider.get("models") or [])]:
        model = normalize_optional_string(entry)
        if not model or model in seen:
            continue
        seen.add(model)
        models.append(model)

    entries: list[VoiceModelCatalogEntry] = []
    for model in models:
        catalog_entry: VoiceModelCatalogEntry = {
            "kind": "voice",
            "provider": provider["id"],
            "model": model,
            "source": "static",
            "capabilities": capabilities,
        }
        if provider.get("label"):
            catalog_entry["label"] = provider["label"]
        if model == provider.get("default_model"):
            catalog_entry["default"] = True
        if modes is not None:
            catalog_entry["modes"] = list(modes)
        entries.append(catalog_entry)
    return entries
