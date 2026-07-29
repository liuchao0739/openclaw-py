import re
from typing import List, Optional

from .types import MediaUnderstandingOutput

MEDIA_PLACEHOLDER_TOKEN = r"<media:[^>]+>(?:\s*\([^)]*\))?"
MEDIA_PLACEHOLDER_RE = re.compile(r"^(?:" + MEDIA_PLACEHOLDER_TOKEN + r"\s*)+$", re.IGNORECASE)
MEDIA_PLACEHOLDER_TOKEN_RE = re.compile(r"^(?:" + MEDIA_PLACEHOLDER_TOKEN + r"\s*)+", re.IGNORECASE)


def extract_media_user_text(body: Optional[str]) -> Optional[str]:
    trimmed = (body or "").strip()
    if not trimmed:
        return None
    if MEDIA_PLACEHOLDER_RE.match(trimmed):
        return None
    cleaned = MEDIA_PLACEHOLDER_TOKEN_RE.sub("", trimmed).strip()
    return cleaned or None


def _format_section(
    title: str,
    kind: str,
    text: str,
    user_text: Optional[str] = None,
) -> str:
    lines = [f"[{title}]"]
    if user_text:
        lines.append(f"User text:\n{user_text}")
    lines.append(f"{kind}:\n{text}")
    return "\n".join(lines)


def format_media_understanding_body(
    body: Optional[str],
    outputs: List[MediaUnderstandingOutput],
) -> str:
    filtered = [o for o in outputs if o.get("text", "").strip()]
    if len(filtered) == 0:
        return body or ""

    user_text = extract_media_user_text(body)
    sections: List[str] = []
    if user_text and len(filtered) > 1:
        sections.append(f"User text:\n{user_text}")

    counts: dict = {}
    for output in filtered:
        k = output["kind"]
        counts[k] = counts.get(k, 0) + 1
    seen: dict = {}

    for output in filtered:
        k = output["kind"]
        count = counts.get(k, 1)
        next_idx = seen.get(k, 0) + 1
        seen[k] = next_idx
        suffix = f" {next_idx}/{count}" if count > 1 else ""
        single_user_text = user_text if len(filtered) == 1 else None
        if k == "audio.transcription":
            sections.append(_format_section(f"Audio{suffix}", "Transcript", output["text"], single_user_text))
        elif k == "image.description":
            sections.append(_format_section(f"Image{suffix}", "Description", output["text"], single_user_text))
        else:
            sections.append(_format_section(f"Video{suffix}", "Description", output["text"], single_user_text))

    return "\n\n".join(sections).strip()


def format_audio_transcripts(outputs: List[MediaUnderstandingOutput]) -> str:
    if len(outputs) == 1:
        return outputs[0]["text"]
    return "\n\n".join(f"Audio {i + 1}:\n{o['text']}" for i, o in enumerate(outputs))
