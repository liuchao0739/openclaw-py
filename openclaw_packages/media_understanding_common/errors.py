from typing import Literal, Optional

MediaUnderstandingSkipReason = Literal["maxBytes", "timeout", "unsupported", "empty", "blocked", "tooSmall"]


class MediaUnderstandingSkipError(Exception):
    def __init__(self, reason: MediaUnderstandingSkipReason, message: str) -> None:
        super().__init__(message)
        self.reason = reason
        self.name = "MediaUnderstandingSkipError"


def is_media_understanding_skip_error(err) -> bool:
    return isinstance(err, MediaUnderstandingSkipError)
