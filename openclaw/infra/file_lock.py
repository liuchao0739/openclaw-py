from __future__ import annotations

import fcntl
import os
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any


class FileLockTimeoutError(Exception):
    pass


FILE_LOCK_TIMEOUT_ERROR_CODE = "FILE_LOCK_TIMEOUT"


def acquire_file_lock(
    lock_path: str,
    options: dict[str, Any] | None = None,
) -> int:
    options = options or {}
    timeout_ms = options.get("timeoutMs", 30000)
    poll_interval_ms = options.get("pollIntervalMs", 50)
    lock_dir = Path(lock_path).parent
    lock_dir.mkdir(parents=True, exist_ok=True)
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR)
    start = time.monotonic()
    while True:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return fd
        except (OSError, IOError):
            elapsed = (time.monotonic() - start) * 1000
            if elapsed >= timeout_ms:
                os.close(fd)
                raise FileLockTimeoutError(
                    f"Could not acquire file lock at {lock_path} within {timeout_ms}ms"
                )
            time.sleep(poll_interval_ms / 1000.0)


def release_file_lock(fd: int) -> None:
    try:
        fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


def with_file_lock(
    lock_path: str,
    options: dict[str, Any] | None = None,
    fn: Callable[[], Any] | None = None,
) -> Any:
    fd = acquire_file_lock(lock_path, options)
    try:
        if fn:
            return fn()
        return None
    finally:
        release_file_lock(fd)


def drain_file_lock_state_for_test() -> None:
    pass


def reset_file_lock_state_for_test() -> None:
    pass
