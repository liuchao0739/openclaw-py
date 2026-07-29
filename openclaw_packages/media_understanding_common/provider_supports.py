from typing import Optional

from .types import MediaUnderstandingCapability, MediaUnderstandingProvider


def provider_supports_capability(
    provider: Optional[MediaUnderstandingProvider],
    capability: MediaUnderstandingCapability,
) -> bool:
    if not provider:
        return False
    if capability == "audio":
        return bool(provider.get("transcribeAudio"))
    if capability == "image":
        return bool(provider.get("describeImage"))
    return bool(provider.get("describeVideo"))
