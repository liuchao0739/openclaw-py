"""Public barrel for speech-core voice model and speaker helpers.

Mirrors packages/speech-core/voice-models.ts and packages/speech-core/speaker.ts.
"""

from __future__ import annotations

from .speaker import (
    SpeakerSelectionConfig,
    with_speaker_selection_compat,
    with_speaker_selection_fallback_compat,
)
from .voice_models import (
    VoiceModelCapabilities,
    VoiceModelCapability,
    VoiceModelCatalogEntry,
    VoiceModelProvider,
    VoiceModelRef,
    VoiceProviderCandidate,
    find_voice_model_provider,
    get_voice_provider_config,
    provider_matches_id,
    resolve_primary_voice_provider_candidate,
    resolve_supported_voice_model_refs,
    resolve_voice_model_refs,
    resolve_voice_provider_candidates,
    synthesize_voice_model_catalog_entries,
    voice_provider_supports_model,
)

__all__ = [
    "SpeakerSelectionConfig",
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
    "with_speaker_selection_compat",
    "with_speaker_selection_fallback_compat",
]
