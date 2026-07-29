from .media_understanding_provider import deepgram_media_understanding_provider
from .realtime_transcription_provider import build_deepgram_realtime_transcription_provider


def _register(api: dict) -> None:
    api["registerMediaUnderstandingProvider"](deepgram_media_understanding_provider)
    api["registerRealtimeTranscriptionProvider"](build_deepgram_realtime_transcription_provider())


plugin_entry: dict = {
    "id": "deepgram",
    "name": "Deepgram Media Understanding",
    "description": "Bundled Deepgram audio transcription provider",
    "register": _register,
}
