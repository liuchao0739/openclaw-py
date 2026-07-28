"""Chat envelope helpers parse and format channel prefixes in chat text."""

from __future__ import annotations

import re

_ENVELOPE_PREFIX = re.compile(r"^\[([^\]]+)\]\s*")
_ENVELOPE_CHANNELS = [
    "WebChat",
    "WhatsApp",
    "Telegram",
    "Signal",
    "Slack",
    "Discord",
    "Google Chat",
    "iMessage",
    "Teams",
    "Matrix",
    "Zalo",
    "Zalo Personal",
]

_MESSAGE_ID_LINE = re.compile(r"^\s*\[message_id:\s*[^\]]+\]\s*$", re.IGNORECASE)


def _looks_like_envelope_header(header: str) -> bool:
    if re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}Z\b", header):
        return True
    if re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}\b", header):
        return True
    return any(header.startswith(f"{label} ") for label in _ENVELOPE_CHANNELS)


def strip_envelope(text: str) -> str:
    match = _ENVELOPE_PREFIX.match(text)
    if not match:
        return text
    header = match.group(1) or ""
    if not _looks_like_envelope_header(header):
        return text
    return text[len(match.group(0)):]


def strip_message_id_hints(text: str) -> str:
    if "[message_id:" not in text.lower():
        return text
    lines = re.split(r"\r?\n", text)
    filtered = [line for line in lines if not _MESSAGE_ID_LINE.match(line)]
    return text if len(filtered) == len(lines) else "\n".join(filtered)
