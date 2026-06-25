"""Shared queue type contracts for admission, drain, and fallback handling."""

from __future__ import annotations

from typing import Any, Literal, TypedDict

QueueMode = Literal["steer", "followup", "collect", "interrupt"]
QueueDropPolicy = Literal["old", "new", "summarize"]
QueueDedupeMode = Literal["message-id", "prompt", "none"]


class QueueSettings(TypedDict, total=False):
    mode: QueueMode
    debounceMs: int
    cap: int
    dropPolicy: QueueDropPolicy


class FollowupRunDeferredError(Exception):
    """Raised when a follow-up run is deferred."""

    def __init__(self, message: str = "Follow-up run deferred") -> None:
        super().__init__(message)
        self.name = "FollowupRunDeferredError"


def is_followup_run_deferred_error(error: BaseException) -> bool:
    """Check if an error is a FollowupRunDeferredError."""
    return isinstance(error, FollowupRunDeferredError)


class FollowupRun(TypedDict, total=False):
    prompt: str
    admissionSessionId: str
    transcriptPrompt: str
    enqueuedAt: int
    messageId: str
    summaryLine: str
    images: list[dict[str, Any]]
    imageOrder: list[dict[str, Any]]
    originatingChannel: str
    originatingTo: str
    originatingAccountId: str
    originatingThreadId: str | int
    deliveryCorrelations: list[dict[str, Any]]
    queuedLifecycle: dict[str, Any]


class QueuedReply(TypedDict, total=False):
    prompt: str
    enqueuedAt: int
    mode: QueueMode
    messageId: str
    images: list[dict[str, Any]]
