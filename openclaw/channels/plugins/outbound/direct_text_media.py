"""Direct text and media outbound formatting."""

from __future__ import annotations

from typing import Any


def format_direct_text_payload(
    text: str,
    media_urls: list[str] | None = None,
) -> dict[str, Any]:
    """Format a direct text + media payload for outbound delivery."""
    payload: dict[str, Any] = {"text": text}
    if media_urls:
        payload["mediaUrls"] = media_urls
    return payload


def split_text_and_media(payload: dict[str, Any]) -> tuple[str, list[str]]:
    """Split a payload into text and media URL components."""
    text = payload.get("text", "")
    media_urls = payload.get("mediaUrls", [])
    if not isinstance(media_urls, list):
        media_urls = []
    return text, media_urls
