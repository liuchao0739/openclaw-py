from .audio import transcribe_deepgram_audio

deepgram_media_understanding_provider: dict = {
    "id": "deepgram",
    "capabilities": ["audio"],
    "defaultModels": {"audio": "nova-3"},
    "autoPriority": {"audio": 30},
    "transcribeAudio": transcribe_deepgram_audio,
}
