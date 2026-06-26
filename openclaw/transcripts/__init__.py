"""Transcripts package — manual source provider."""

from .manual_source import (
    manual_transcript_source_provider,
    parse_speaker_line,
)

__all__ = [
    "manual_transcript_source_provider",
    "parse_speaker_line",
]
