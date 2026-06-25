"""Queue normalization helpers."""

from __future__ import annotations

from typing import Any

from openclaw.auto_reply.reply.queue.types import FollowupRun


def normalize_followup_run(run: dict[str, Any]) -> FollowupRun:
    """Normalize a follow-up run into a standard shape."""
    import time

    normalized: dict[str, Any] = {
        "prompt": (run.get("prompt") or "").strip(),
        "enqueuedAt": run.get("enqueuedAt") or int(time.time() * 1000),
    }

    for key in (
        "admissionSessionId", "transcriptPrompt", "messageId", "summaryLine",
        "images", "imageOrder", "originatingChannel", "originatingTo",
        "originatingAccountId", "originatingThreadId",
        "deliveryCorrelations", "queuedLifecycle",
    ):
        if run.get(key) is not None:
            normalized[key] = run[key]

    return normalized  # type: ignore[return-value]


def dedupe_queue(
    queue: list[FollowupRun],
    mode: str = "message-id",
) -> list[FollowupRun]:
    """Remove duplicate entries from a queue based on dedupe mode."""
    if mode == "none":
        return queue

    seen: set[str] = set()
    result: list[FollowupRun] = []

    for run in queue:
        if mode == "message-id":
            key = run.get("messageId", "")
            if key:
                if key in seen:
                    continue
                seen.add(key)
        elif mode == "prompt":
            key = run.get("prompt", "")
            if key:
                if key in seen:
                    continue
                seen.add(key)
        result.append(run)

    return result


def apply_drop_policy(
    queue: list[FollowupRun],
    cap: int,
    policy: str = "old",
) -> list[FollowupRun]:
    """Apply a drop policy to keep the queue within cap."""
    if len(queue) <= cap:
        return queue

    if policy == "old":
        return queue[-cap:]
    if policy == "new":
        return queue[:cap]
    if policy == "summarize":
        # Keep the first and last entries, summarize the middle
        if cap <= 2:
            return queue[-cap:]
        kept = [queue[0]] + queue[-(cap - 1):]
        return kept
    return queue[-cap:]
