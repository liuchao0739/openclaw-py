from typing import Any, Dict, Optional

SpeakerSelectionConfig = Dict[str, Any]


def _read_string(value: Any) -> Optional[str]:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def with_speaker_selection_compat(config: Optional[SpeakerSelectionConfig]) -> SpeakerSelectionConfig:
    next_config: SpeakerSelectionConfig = dict(config) if config else {}
    speaker_voice = _read_string(next_config.get("speakerVoice"))
    speaker_voice_id = _read_string(next_config.get("speakerVoiceId"))
    voice = _read_string(next_config.get("voice"))
    voice_name = _read_string(next_config.get("voiceName"))
    voice_id = _read_string(next_config.get("voiceId"))
    canonical_voice = speaker_voice or voice or voice_name
    canonical_voice_id = speaker_voice_id or voice_id
    if canonical_voice:
        next_config["speakerVoice"] = canonical_voice
        next_config["voice"] = canonical_voice
        next_config["voiceName"] = canonical_voice
    if canonical_voice_id:
        next_config["speakerVoiceId"] = canonical_voice_id
        next_config["voiceId"] = canonical_voice_id
    return next_config


def with_speaker_selection_fallback_compat(config: Optional[SpeakerSelectionConfig]) -> SpeakerSelectionConfig:
    next_config: SpeakerSelectionConfig = dict(config) if config else {}
    speaker_voice = _read_string(next_config.get("speakerVoice"))
    speaker_voice_id = _read_string(next_config.get("speakerVoiceId"))
    if speaker_voice:
        if next_config.get("voice") is None:
            next_config["voice"] = speaker_voice
        if next_config.get("voiceName") is None:
            next_config["voiceName"] = speaker_voice
    if speaker_voice_id:
        if next_config.get("voiceId") is None:
            next_config["voiceId"] = speaker_voice_id
    return next_config
