"""Media Understanding Common helper module supports format behavior."""

from __future__ import annotations

import re

from .types import MediaUnderstandingOutput

MEDIA_PLACEHOLDER_TOKEN = r"<media:[^>]+>(?:\s*\([^)]*\))?"
MEDIA_PLACEHOLDER_RE = re.compile(rf"^(?:{MEDIA_PLACEHOLDER_TOKEN}\s*)+$", re.IGNORECASE)
MEDIA_PLACEHOLDER_TOKEN_RE = re.compile(rf"^(?:{MEDIA_PLACEHOLDER_TOKEN}\s*)+", re.IGNORECASE)


def extract_media_user_text(body: str | None = None) -> str | None:
    """Extract user-authored text while ignoring synthetic media placeholder tokens."""
    trimmed = body.strip() if isinstance(body, str) else ""
    if not trimmed:
        return None
    if MEDIA_PLACEHOLDER_RE.fullmatch(trimmed):
        return None
    cleaned = MEDIA_PLACEHOLDER_TOKEN_RE.sub("", trimmed).strip()
    return cleaned or None


def _format_section(
    title: str,
    kind: str,
    text: str,
    user_text: str | None = None,
) -> str:
    lines = [f"[{title}]"]
    if user_text:
        lines.append(f"User text:\n{user_text}")
    lines.append(f"{kind}:\n{text}")
    return "\n".join(lines)


def format_media_understanding_body(
    *,
    body: str | None = None,
    outputs: list[MediaUnderstandingOutput],
) -> str:
    """Format media-understanding outputs into the chat body sent back to the model."""
    non_empty_outputs = [output for output in outputs if output.get("text", "").strip()]
    if not non_empty_outputs:
        return body or ""

    user_text = extract_media_user_text(body)
    sections: list[str] = []
    if user_text and len(non_empty_outputs) > 1:
        sections.append(f"User text:\n{user_text}")

    counts: dict[str, int] = {}
    for output in non_empty_outputs:
        kind = output["kind"]
        counts[kind] = counts.get(kind, 0) + 1
    seen: dict[str, int] = {}

    for output in non_empty_outputs:
        kind = output["kind"]
        count = counts.get(kind, 1)
        next_index = seen.get(kind, 0) + 1
        seen[kind] = next_index
        suffix = f" {next_index}/{count}" if count > 1 else ""
        single_output_user_text = user_text if len(non_empty_outputs) == 1 else None
        if kind == "audio.transcription":
            sections.append(
                _format_section(
                    f"Audio{suffix}",
                    "Transcript",
                    output["text"],
                    single_output_user_text,
                ),
            )
            continue
        if kind == "image.description":
            sections.append(
                _format_section(
                    f"Image{suffix}",
                    "Description",
                    output["text"],
                    single_output_user_text,
                ),
            )
            continue
        sections.append(
            _format_section(
                f"Video{suffix}",
                "Description",
                output["text"],
                single_output_user_text,
            ),
        )

    return "\n\n".join(sections).strip()


def format_audio_transcripts(outputs: list[MediaUnderstandingOutput]) -> str:
    """Format one or more audio transcript outputs for legacy transcript-only callers."""
    if len(outputs) == 1:
        return outputs[0]["text"]
    return "\n\n".join(
        f"Audio {index + 1}:\n{output['text']}" for index, output in enumerate(outputs)
    )
