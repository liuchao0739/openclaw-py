"""Platform-specific silence windows for talk/voice turn segmentation."""

from typing import Final

TALK_SILENCE_TIMEOUT_MS_BY_PLATFORM: Final[dict[str, int]] = {
    "macos": 700,
    "android": 700,
    "ios": 900,
}


def describe_talk_silence_timeout_defaults() -> str:
    """Format the talk silence defaults for config help text."""
    macos = TALK_SILENCE_TIMEOUT_MS_BY_PLATFORM["macos"]
    ios = TALK_SILENCE_TIMEOUT_MS_BY_PLATFORM["ios"]
    return f"{macos} ms on macOS and Android, {ios} ms on iOS"
