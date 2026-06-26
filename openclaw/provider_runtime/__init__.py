"""Provider runtime package — operation retry logic.

Mirrors src/provider-runtime/operation-retry.ts. Stub implementation.
"""

from __future__ import annotations

from typing import Any


class OperationRetryPolicy:
    """Retry policy for provider operations."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay_ms: int = 1000,
        max_delay_ms: int = 30000,
        jitter: bool = True,
    ) -> None:
        self.max_retries = max_retries
        self.base_delay_ms = base_delay_ms
        self.max_delay_ms = max_delay_ms
        self.jitter = jitter

    def compute_delay(self, attempt: int) -> int:
        """Compute the delay for a retry attempt (exponential backoff)."""
        delay = min(
            self.base_delay_ms * (2 ** attempt),
            self.max_delay_ms,
        )
        if self.jitter:
            import random
            delay = int(delay * (0.5 + random.random() * 0.5))
        return delay

    def should_retry(self, attempt: int, error: Any) -> bool:
        """Determine if an operation should be retried."""
        if attempt >= self.max_retries:
            return False
        return True


DEFAULT_RETRY_POLICY = OperationRetryPolicy()
