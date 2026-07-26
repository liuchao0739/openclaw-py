"""Capability checks for media-understanding provider objects."""

from __future__ import annotations

from .types import MediaUnderstandingCapability, MediaUnderstandingProvider


def provider_supports_capability(
    provider: MediaUnderstandingProvider | None,
    capability: MediaUnderstandingCapability,
) -> bool:
    """Return true when a provider exposes the method for a media capability."""
    if not provider:
        return False
    if capability == "audio":
        return bool(provider.get("transcribe_audio"))
    if capability == "image":
        return bool(provider.get("describe_image"))
    return bool(provider.get("describe_video"))
