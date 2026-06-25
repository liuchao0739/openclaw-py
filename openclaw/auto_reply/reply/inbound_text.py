"""Normalizes real inbound newline characters while preserving literal escape text."""

from __future__ import annotations


def normalize_inbound_text_newlines(input_text: str) -> str:
    """Normalize actual newline characters (CR+LF and CR to LF).

    Does NOT replace literal backslash-n sequences (\\n) as they may be part of
    Windows paths like C:\\Work\\nxxx\\README.md or user-intended escape sequences.
    """
    return input_text.replace("\r\n", "\n").replace("\r", "\n")


def sanitize_inbound_system_tags(text: str) -> str:
    """Strip inbound system control tags.

    Deferred to security/system_tags module; this stub passes through unchanged
    during the migration window.
    """
    try:
        from openclaw.security.system_tags import sanitize_inbound_system_tags as _sanitize

        return _sanitize(text)
    except Exception:
        return text
