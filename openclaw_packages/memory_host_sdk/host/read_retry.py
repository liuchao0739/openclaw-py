from __future__ import annotations

from typing import Any, Optional

from .retry_utils import retry_async

TRANSIENT_MEMORY_READ_ERRNO = -11
TRANSIENT_MEMORY_READ_CODES = frozenset(["EAGAIN", "EWOULDBLOCK", "EDEADLK"])
TRANSIENT_MEMORY_READ_MESSAGE = "Unknown system error -11"


def _get_errno(error: object) -> Optional[int]:
    if hasattr(error, "errno") and isinstance(error.errno, int):
        return error.errno
    if isinstance(error, OSError) and isinstance(error.errno, int):
        return error.errno
    return None


def _get_code(error: object) -> Optional[str]:
    if hasattr(error, "code") and isinstance(error.code, str):
        return error.code
    return None


def is_transient_memory_read_error(error: object) -> bool:
    code = _get_code(error)
    if code and code in TRANSIENT_MEMORY_READ_CODES:
        return True

    errno = _get_errno(error)
    if errno == TRANSIENT_MEMORY_READ_ERRNO:
        return True

    if isinstance(error, Exception) and TRANSIENT_MEMORY_READ_MESSAGE.lower() in str(error).lower():
        return True

    return False


def retry_transient_memory_read(read_fn, label: str = "memory read") -> Any:
    return retry_async(
        read_fn,
        {
            "attempts": 3,
            "minDelayMs": 25,
            "maxDelayMs": 50,
            "label": label,
            "shouldRetry": lambda error, _attempt: is_transient_memory_read_error(error),
        },
    )
