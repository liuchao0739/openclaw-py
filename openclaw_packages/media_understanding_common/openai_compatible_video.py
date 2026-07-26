"""OpenAI-compatible video request/response helpers."""

from __future__ import annotations

import base64
from typing import Any, TypedDict

from openclaw.packages.normalization_core import normalize_optional_string

__all__ = [
    "OpenAiCompatibleVideoPayload",
    "build_open_ai_compatible_video_request_body",
    "coerce_open_ai_compatible_video_text",
    "resolve_media_understanding_string",
]


class OpenAiCompatibleVideoPayload(TypedDict, total=False):
    choices: list[dict[str, Any]]


def resolve_media_understanding_string(value: str | None, fallback: str) -> str:
    """Trim optional strings, falling back when empty."""
    return normalize_optional_string(value) or fallback


def coerce_open_ai_compatible_video_text(payload: OpenAiCompatibleVideoPayload) -> str | None:
    """Coerce text from OpenAI-compatible content or reasoning fields."""
    choices = payload.get("choices") or []
    if not choices:
        return None
    message = choices[0].get("message")
    if not isinstance(message, dict):
        return None

    content = message.get("content")
    if isinstance(content, str):
        trimmed = content.strip()
        if trimmed:
            return trimmed
    if isinstance(content, list):
        text = "\n".join(
            part.strip()
            for part in (
                item.get("text", "").strip()
                for item in content
                if isinstance(item, dict) and isinstance(item.get("text"), str)
            )
            if part
        )
        if text:
            return text

    reasoning_content = message.get("reasoning_content")
    if isinstance(reasoning_content, str):
        trimmed = reasoning_content.strip()
        if trimmed:
            return trimmed
    return None


def build_open_ai_compatible_video_request_body(
    *,
    model: str,
    prompt: str,
    mime: str,
    buffer: bytes,
) -> dict[str, Any]:
    """Build an OpenAI-compatible request body with an inline data URL video."""
    encoded = base64.b64encode(buffer).decode("ascii")
    return {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "video_url",
                        "video_url": {
                            "url": f"data:{mime};base64,{encoded}",
                        },
                    },
                ],
            },
        ],
    }
