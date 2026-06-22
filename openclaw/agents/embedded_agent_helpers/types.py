"""Embedded agent helper types."""

from __future__ import annotations

from typing import Literal, TypedDict

FailoverReason = Literal[
    "auth",
    "auth_permanent",
    "format",
    "rate_limit",
    "overloaded",
    "billing",
    "server_error",
    "timeout",
    "model_not_found",
    "session_expired",
    "empty_response",
    "no_error_details",
    "unclassified",
    "unknown",
]


class EmbeddedContextFile(TypedDict):
    path: str
    content: str