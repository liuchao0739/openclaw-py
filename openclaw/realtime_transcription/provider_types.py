"""Realtime transcription provider types describe streaming transcription providers.

Mirrors src/realtime-transcription/provider-types.ts.
"""

from __future__ import annotations

from typing import Any, Callable, Protocol, TypedDict, runtime_checkable

RealtimeTranscriptionProviderId = str


class RealtimeTranscriptionSessionCallbacks(TypedDict, total=False):
    onPartial: Callable[[str], None]
    onTranscript: Callable[[str], None]
    onSpeechStart: Callable[[], None]
    onError: Callable[[Exception], None]


@runtime_checkable
class RealtimeTranscriptionSession(Protocol):
    """Runtime control surface for a realtime transcription session."""

    async def connect(self) -> None: ...
    def send_audio(self, audio: bytes) -> None: ...
    def close(self) -> None: ...
    def is_connected(self) -> bool: ...
