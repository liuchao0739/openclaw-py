"""Media-understanding skip error used for non-fatal attachment omissions."""

from __future__ import annotations

from typing import Literal

MediaUnderstandingSkipReason = Literal[
    "maxBytes",
    "timeout",
    "unsupported",
    "empty",
    "blocked",
    "tooSmall",
]


class MediaUnderstandingSkipError(Exception):
    """Error used when a media attachment should be skipped without failing the whole request."""

    def __init__(self, reason: MediaUnderstandingSkipReason, message: str) -> None:
        super().__init__(message)
        self.reason = reason


def is_media_understanding_skip_error(err: object) -> bool:
    """Narrow unknown errors to media-understanding skip errors."""
    return isinstance(err, MediaUnderstandingSkipError)
