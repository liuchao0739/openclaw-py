"""Provides manual transcript source entries for user-supplied transcript text.

Mirrors src/transcripts/manual-source.ts.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

_SPEAKER_LINE_RE = re.compile(r"^([^:\n]{1,80}):\s+(.+)$")


def parse_speaker_line(line: str) -> dict[str, str | None]:
    """Parse a speaker line into speaker label and text."""
    if not isinstance(line, str):
        return {"speaker_label": None, "text": ""}
    trimmed = line.strip()
    match = _SPEAKER_LINE_RE.match(trimmed)
    if not match:
        return {"speaker_label": None, "text": trimmed}
    return {
        "speaker_label": match.group(1).strip(),
        "text": (match.group(2) or "").strip(),
    }


async def _import_transcript(request: dict[str, Any]) -> list[dict[str, Any]]:
    """Import transcript text into utterance entries."""
    text = request.get("text", "")
    session = request.get("session", {})
    session_id = session.get("sessionId", "session")
    default_speaker = request.get("speakerLabel", "Speaker")
    now = datetime.now(timezone.utc).isoformat()
    result: list[dict[str, Any]] = []
    lines = re.split(r"\r?\n", text) if isinstance(text, str) else []
    index = 0
    for line in lines:
        entry = parse_speaker_line(line)
        if not entry["text"]:
            continue
        index += 1
        result.append({
            "id": f"{session_id}-{index}",
            "sessionId": session_id,
            "startedAt": now,
            "final": True,
            "speaker": {
                "label": entry["speaker_label"] or default_speaker,
            },
            "text": entry["text"],
        })
    return result


manual_transcript_source_provider: dict[str, Any] = {
    "id": "manual-transcript",
    "aliases": ["import", "transcript"],
    "name": "Manual Transcript Import",
    "sourceKinds": ["posthoc-transcript"],
    "importTranscript": _import_transcript,
}
