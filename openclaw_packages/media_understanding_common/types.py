from typing import Any, List, Literal, Optional, TypedDict

MediaUnderstandingKind = Literal["audio.transcription", "video.description", "image.description"]
MediaUnderstandingCapability = Literal["image", "audio", "video"]


class MediaUnderstandingCapabilityEntry(TypedDict, total=False):
    capabilities: List[MediaUnderstandingCapability]


MediaUnderstandingCapabilityRegistry = dict


class MediaAttachment(TypedDict, total=False):
    path: str
    url: str
    mime: str
    index: int
    alreadyTranscribed: bool


class MediaUnderstandingOutput(TypedDict):
    kind: MediaUnderstandingKind
    attachmentIndex: int
    text: str
    provider: str


class MediaUnderstandingProvider(TypedDict, total=False):
    id: str
    capabilities: List[MediaUnderstandingCapability]
    transcribeAudio: Any
    describeVideo: Any
    describeImage: Any
    describeImages: Any
    extractStructured: Any
