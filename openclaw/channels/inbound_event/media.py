"""Channel inbound event media payload builder."""

from __future__ import annotations

from typing import Any


def build_channel_inbound_media_payload(
    media_facts: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Build a normalized media payload from inbound media facts.

    Converts raw media attachment metadata into the content block format
    used by the reply pipeline.
    """
    if not media_facts:
        return []

    payloads: list[dict[str, Any]] = []
    for media in media_facts:
        if not isinstance(media, dict):
            continue

        mime_type = media.get("mimeType") or media.get("mime_type") or "image/unknown"
        data = media.get("data") or media.get("url") or ""
        if not data:
            continue

        payload: dict[str, Any] = {
            "type": "image",
            "mimeType": mime_type,
            "data": data,
        }

        # Optional metadata
        for key in ("caption", "filename", "width", "height", "fileSize"):
            if media.get(key) is not None:
                payload[key] = media[key]

        payloads.append(payload)

    return payloads


def normalize_inbound_media_facts(
    raw: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Normalize raw media attachment metadata into a consistent shape."""
    if not raw:
        return []

    normalized: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        facts: dict[str, Any] = {
            "mimeType": item.get("mimeType") or item.get("mime_type") or "image/unknown",
            "data": item.get("data") or item.get("url") or "",
        }
        for key in ("caption", "filename", "width", "height", "fileSize", "sourceUrl"):
            if item.get(key) is not None:
                facts[key] = item[key]
        if facts["data"]:
            normalized.append(facts)

    return normalized
