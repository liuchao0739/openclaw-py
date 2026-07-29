import base64
from typing import Any, List, Optional, TypedDict, Union


class OpenAiCompatibleVideoMessage(TypedDict, total=False):
    content: Union[str, List[dict]]
    reasoning_content: str


class OpenAiCompatibleVideoChoice(TypedDict, total=False):
    message: OpenAiCompatibleVideoMessage


class OpenAiCompatibleVideoPayload(TypedDict, total=False):
    choices: List[OpenAiCompatibleVideoChoice]


def resolve_media_understanding_string(value: Optional[str], fallback: str) -> str:
    trimmed = value.strip() if value else ""
    return trimmed or fallback


def coerce_openai_compatible_video_text(payload: OpenAiCompatibleVideoPayload) -> Optional[str]:
    choices = payload.get("choices")
    if not choices:
        return None
    message = choices[0].get("message") if choices else None
    if not message:
        return None
    content = message.get("content")
    if isinstance(content, str) and content.strip():
        return content.strip()
    if isinstance(content, list):
        parts = []
        for part in content:
            text = part.get("text", "").strip() if isinstance(part, dict) else ""
            if text:
                parts.append(text)
        text = "\n".join(parts)
        if text:
            return text
    reasoning = message.get("reasoning_content")
    if isinstance(reasoning, str) and reasoning.strip():
        return reasoning.strip()
    return None


def build_openai_compatible_video_request_body(
    model: str,
    prompt: str,
    mime: str,
    buffer: bytes,
) -> dict:
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
