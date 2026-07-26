"""Shared media-understanding provider, attachment, output, and capability contracts."""

from __future__ import annotations

from typing import Any, Literal, TypedDict

MediaUnderstandingKind = Literal[
    "audio.transcription",
    "video.description",
    "image.description",
]

MediaUnderstandingCapability = Literal["image", "audio", "video"]

MediaUnderstandingCapabilityRegistry = dict[
    str,
    dict[str, list[MediaUnderstandingCapability] | None],
]


class MediaAttachment(TypedDict, total=False):
    path: str
    url: str
    mime: str
    index: int
    already_transcribed: bool


class MediaUnderstandingOutput(TypedDict, total=False):
    kind: MediaUnderstandingKind
    attachment_index: int
    text: str
    provider: str
    model: str


class MediaUnderstandingProvider(TypedDict, total=False):
    id: str
    capabilities: list[MediaUnderstandingCapability]
    transcribe_audio: Any
    describe_video: Any
    describe_image: Any
    describe_images: Any
    extract_structured: Any
