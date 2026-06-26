"""Unauthorized flood guard rate-limits repeated unauthorized role errors on one
WebSocket connection.

Mirrors src/gateway/server/ws-connection/unauthorized-flood-guard.ts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

DEFAULT_CLOSE_AFTER = 10
DEFAULT_LOG_EVERY = 100

# ErrorCodes.INVALID_REQUEST equivalent.
_INVALID_REQUEST_CODE = "invalid_request"


@dataclass
class UnauthorizedFloodDecision:
    should_close: bool
    should_log: bool
    count: int
    suppressed_since_last_log: int


class UnauthorizedFloodGuard:
    """Per-connection guard that suppresses noisy unauthorized-role retries."""

    def __init__(
        self,
        options: Mapping[str, Any] | None = None,
    ) -> None:
        opts = options or {}
        self._close_after = _resolve_integer_option(
            opts.get("closeAfter"), DEFAULT_CLOSE_AFTER, min_val=1
        )
        self._log_every = _resolve_integer_option(
            opts.get("logEvery"), DEFAULT_LOG_EVERY, min_val=1
        )
        self._count = 0
        self._suppressed_since_last_log = 0

    def register_unauthorized(self) -> UnauthorizedFloodDecision:
        """Count one unauthorized failure and decide when to log or close."""
        self._count += 1
        should_close = self._count > self._close_after
        should_log = (
            self._count == 1
            or self._count % self._log_every == 0
            or should_close
        )

        if not should_log:
            self._suppressed_since_last_log += 1
            return UnauthorizedFloodDecision(
                should_close=should_close,
                should_log=False,
                count=self._count,
                suppressed_since_last_log=0,
            )

        suppressed = self._suppressed_since_last_log
        self._suppressed_since_last_log = 0
        return UnauthorizedFloodDecision(
            should_close=should_close,
            should_log=True,
            count=self._count,
            suppressed_since_last_log=suppressed,
        )

    def reset(self) -> None:
        self._count = 0
        self._suppressed_since_last_log = 0


def is_unauthorized_role_error(error: Mapping[str, Any] | None) -> bool:
    """Identify role-auth failures that should feed the flood guard."""
    if not error:
        return False
    return (
        error.get("code") == _INVALID_REQUEST_CODE
        and isinstance(error.get("message"), str)
        and error["message"].startswith("unauthorized role:")
    )


def _resolve_integer_option(
    value: Any, default: int, *, min_val: int = 1
) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return max(min_val, value)
    if isinstance(value, float) and not (value != value or value in (float("inf"), float("-inf"))):
        return max(min_val, int(value))
    return default
