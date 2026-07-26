"""Discord plugin module implements shared interactive behavior."""

from __future__ import annotations

from typing import Any


def normalize_message_presentation(value: object) -> dict[str, Any] | None:
    return value if isinstance(value, dict) else None


def normalize_interactive_reply(value: object) -> dict[str, Any] | None:
    return value if isinstance(value, dict) else None


def build_discord_interactive_components(interactive: dict[str, Any] | None) -> dict[str, Any] | None:
    if not interactive:
        return None
    blocks = interactive.get("blocks")
    if not isinstance(blocks, list) or not blocks:
        return None
    return {"blocks": blocks}


def build_discord_presentation_components(
    presentation: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not presentation:
        return None
    blocks: list[dict[str, Any]] = []
    title = presentation.get("title")
    if isinstance(title, str) and title.strip():
        blocks.append({"type": "text", "text": title})
    for block in presentation.get("blocks") or []:
        if not isinstance(block, dict):
            continue
        if block.get("type") in ("text", "context") and isinstance(block.get("text"), str):
            text = block["text"].strip()
            if text:
                blocks.append({"type": "text", "text": text})
    return {"blocks": blocks} if blocks else None


__all__ = [
    "build_discord_interactive_components",
    "build_discord_presentation_components",
    "normalize_interactive_reply",
    "normalize_message_presentation",
]
