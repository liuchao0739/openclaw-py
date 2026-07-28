from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional


def resolve_batch_completion_from_status(
    status: str,
    batch_id: str,
    provider_id: str,
) -> dict:
    return {
        "status": status,
        "batchId": batch_id,
        "providerId": provider_id,
    }


def resolve_completed_batch_result(result: dict) -> list:
    return result.get("output", [])


def throw_if_batch_terminal_failure(status: dict) -> None:
    if status.get("status") in ("failed", "cancelled", "expired"):
        error_message = status.get("error", "Unknown batch error")
        raise Exception(f"Batch failed: {error_message}")
