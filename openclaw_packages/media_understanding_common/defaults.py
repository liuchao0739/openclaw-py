from typing import Dict, Optional

from .types import MediaUnderstandingCapability

MB = 1024 * 1024

DEFAULT_MAX_CHARS = 500
DEFAULT_MAX_CHARS_BY_CAPABILITY: Dict[MediaUnderstandingCapability, Optional[int]] = {
    "image": DEFAULT_MAX_CHARS,
    "audio": None,
    "video": DEFAULT_MAX_CHARS,
}
DEFAULT_MAX_BYTES: Dict[MediaUnderstandingCapability, int] = {
    "image": 10 * MB,
    "audio": 20 * MB,
    "video": 50 * MB,
}
DEFAULT_TIMEOUT_SECONDS: Dict[MediaUnderstandingCapability, int] = {
    "image": 60,
    "audio": 60,
    "video": 120,
}
DEFAULT_PROMPT: Dict[MediaUnderstandingCapability, str] = {
    "image": "Describe the image.",
    "audio": "Transcribe the audio.",
    "video": "Describe the video.",
}
DEFAULT_VIDEO_MAX_BASE64_BYTES = 70 * MB
CLI_OUTPUT_MAX_BUFFER = 5 * MB
DEFAULT_MEDIA_CONCURRENCY = 2
MIN_AUDIO_FILE_BYTES = 1024
