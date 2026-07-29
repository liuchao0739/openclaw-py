from typing import Any, List, Literal, Optional, Sequence, TypedDict

VoiceModelCapability = Literal["tts", "realtime_transcription", "realtime_voice"]


class VoiceModelCapabilities(TypedDict, total=False):
    tts: bool
    realtime_transcription: bool
    realtime_voice: bool


class VoiceModelRef(TypedDict, total=False):
    provider: str
    model: str
    timeoutMs: int


class VoiceModelProvider(TypedDict, total=False):
    id: str
    aliases: Sequence[str]
    label: str
    defaultModel: Optional[str]
    models: Sequence[str]


class VoiceModelCatalogEntry(TypedDict, total=False):
    kind: Literal["voice"]
    provider: str
    model: str
    source: Literal["static"]
    capabilities: VoiceModelCapabilities
    label: str
    default: bool
    modes: Sequence[str]


class VoiceProviderCandidate(TypedDict, total=False):
    provider: str
    voiceModel: VoiceModelRef


def _normalize_string(value: Any) -> Optional[str]:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _normalize_lowercase_string(value: Any) -> Optional[str]:
    normalized = _normalize_string(value)
    return normalized.lower() if normalized else None


def _normalize_timeout_ms(value: Any) -> Optional[int]:
    if isinstance(value, (int, float)) and value == value and value > 0:
        return int(value)
    return None


def _parse_voice_model_ref(value: Any) -> Optional[VoiceModelRef]:
    raw = _normalize_string(value)
    if not raw:
        return None
    slash_index = raw.find("/")
    if slash_index <= 0 or slash_index == len(raw) - 1:
        return None
    provider = _normalize_lowercase_string(raw[:slash_index])
    model = _normalize_string(raw[slash_index + 1:])
    if provider and model:
        return {"provider": provider, "model": model}
    return None


def _same_provider(left: Optional[str], right: Optional[str]) -> bool:
    normalized_left = _normalize_lowercase_string(left)
    return bool(normalized_left and normalized_left == _normalize_lowercase_string(right))


def provider_matches_id(provider: VoiceModelProvider, provider_id: Optional[str]) -> bool:
    if _same_provider(provider.get("id"), provider_id):
        return True
    for alias in (provider.get("aliases") or []):
        if _same_provider(alias, provider_id):
            return True
    return False


def find_voice_model_provider(
    providers: Sequence[VoiceModelProvider],
    provider_id: Optional[str] = None,
) -> Optional[VoiceModelProvider]:
    for provider in providers:
        if provider_matches_id(provider, provider_id):
            return provider
    return None


def voice_provider_supports_model(
    provider: Optional[VoiceModelProvider],
    model: Any,
) -> bool:
    if not provider:
        return False
    normalized_model = _normalize_string(model)
    candidates = [provider.get("defaultModel"), *(provider.get("models") or [])]
    for candidate in candidates:
        if _normalize_string(candidate) == normalized_model:
            return True
    return False


def resolve_voice_model_refs(config: Any) -> List[VoiceModelRef]:
    if isinstance(config, str):
        parsed = _parse_voice_model_ref(config)
        return [parsed] if parsed else []
    if not isinstance(config, dict) or isinstance(config, list):
        return []
    timeout_ms = _normalize_timeout_ms(config.get("timeoutMs"))
    refs: List[VoiceModelRef] = []

    def add_ref(value: Any) -> None:
        parsed = _parse_voice_model_ref(value)
        if parsed:
            ref: VoiceModelRef = dict(parsed)
            if timeout_ms is not None:
                ref["timeoutMs"] = timeout_ms
            refs.append(ref)

    add_ref(config.get("primary"))
    fallbacks = config.get("fallbacks")
    if isinstance(fallbacks, list):
        for fallback in fallbacks:
            add_ref(fallback)
    return refs


def resolve_supported_voice_model_refs(
    config: Any,
    providers: Sequence[VoiceModelProvider],
    provider_id: Optional[str] = None,
) -> List[VoiceModelRef]:
    result: List[VoiceModelRef] = []
    for ref in resolve_voice_model_refs(config):
        provider = find_voice_model_provider(providers=providers, provider_id=ref["provider"])
        if not provider:
            continue
        if provider_id and not provider_matches_id(provider, provider_id):
            continue
        if voice_provider_supports_model(provider, ref["model"]):
            result.append({**ref, "provider": provider["id"]})
    return result


def resolve_voice_provider_candidates(
    primary_provider: str,
    providers: Sequence[VoiceModelProvider],
    voice_model_config: Any = None,
) -> List[VoiceProviderCandidate]:
    primary = find_voice_model_provider(providers=providers, provider_id=primary_provider)
    primary_id = primary["id"] if primary else primary_provider
    candidates: List[VoiceProviderCandidate] = []
    seen_providers: set = set()

    def add_candidate(candidate: VoiceProviderCandidate) -> None:
        candidates.append(candidate)
        seen_providers.add(candidate["provider"])

    refs = resolve_supported_voice_model_refs(config=voice_model_config, providers=providers)
    primary_refs = [r for r in refs if r["provider"] == primary_id]
    for voice_model in primary_refs:
        add_candidate({"provider": primary_id, "voiceModel": voice_model})
    if len(primary_refs) == 0:
        add_candidate({"provider": primary_id})
    for voice_model in refs:
        if voice_model["provider"] != primary_id:
            add_candidate({"provider": voice_model["provider"], "voiceModel": voice_model})
    for provider in providers:
        if provider["id"] not in seen_providers:
            add_candidate({"provider": provider["id"]})
    return candidates


def resolve_primary_voice_provider_candidate(
    primary_provider: str,
    providers: Sequence[VoiceModelProvider],
    voice_model_config: Any = None,
) -> VoiceProviderCandidate:
    primary = find_voice_model_provider(providers=providers, provider_id=primary_provider)
    provider_id = primary["id"] if primary else primary_provider
    refs = resolve_supported_voice_model_refs(
        config=voice_model_config,
        providers=providers,
        provider_id=provider_id,
    )
    voice_model = refs[0] if refs else None
    if voice_model:
        return {"provider": provider_id, "voiceModel": voice_model}
    return {"provider": provider_id}


def get_voice_provider_config(
    provider_configs: dict,
    provider: VoiceModelProvider,
    configured_provider_id: Optional[str] = None,
) -> dict:
    candidates = [
        c for c in [
            _normalize_string(configured_provider_id),
            provider.get("id"),
            *(provider.get("aliases") or []),
        ] if c is not None
    ]
    configured_keys = list(provider_configs.keys())
    for candidate in candidates:
        if candidate in provider_configs:
            return provider_configs[candidate] or {}
        normalized_candidate = _normalize_lowercase_string(candidate)
        for key in configured_keys:
            if _normalize_lowercase_string(key) == normalized_candidate:
                return provider_configs[key] or {}
    return {}


def synthesize_voice_model_catalog_entries(
    provider: VoiceModelProvider,
    capabilities: VoiceModelCapabilities,
    modes: Optional[Sequence[str]] = None,
) -> List[VoiceModelCatalogEntry]:
    seen: set = set()
    raw_models = [provider.get("defaultModel"), *(provider.get("models") or [])]
    models: List[str] = []
    for entry in raw_models:
        model = _normalize_string(entry)
        if not model or model in seen:
            continue
        seen.add(model)
        models.append(model)
    result: List[VoiceModelCatalogEntry] = []
    for model in models:
        entry: VoiceModelCatalogEntry = {
            "kind": "voice",
            "provider": provider["id"],
            "model": model,
            "source": "static",
            "capabilities": capabilities,
        }
        if provider.get("label"):
            entry["label"] = provider["label"]
        if model == provider.get("defaultModel"):
            entry["default"] = True
        if modes:
            entry["modes"] = modes
        result.append(entry)
    return result
