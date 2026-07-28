from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any


class FileLockError(Exception):
    pass


class FileLockTimeoutError(FileLockError):
    pass


def acquire_file_lock(
    lock_path: str,
    timeout_ms: int = 30000,
    poll_interval_ms: int = 100,
) -> Any:
    import fcntl
    import time

    lock_dir = os.path.dirname(lock_path)
    if lock_dir:
        os.makedirs(lock_dir, exist_ok=True)

    start_time = time.time() * 1000
    while True:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_RDWR)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return fd
            except (OSError, IOError):
                os.close(fd)
        except (OSError, IOError):
            pass

        elapsed = (time.time() * 1000) - start_time
        if elapsed >= timeout_ms:
            raise FileLockTimeoutError(
                f"Timed out waiting for file lock: {lock_path}"
            )

        time.sleep(poll_interval_ms / 1000.0)


def release_file_lock(fd: int) -> None:
    import fcntl
    try:
        fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


class FileLock:
    def __init__(
        self,
        lock_path: str,
        timeout_ms: int = 30000,
        poll_interval_ms: int = 100,
    ):
        self.lock_path = lock_path
        self.timeout_ms = timeout_ms
        self.poll_interval_ms = poll_interval_ms
        self._fd: int | None = None

    def acquire(self) -> "FileLock":
        self._fd = acquire_file_lock(
            self.lock_path,
            timeout_ms=self.timeout_ms,
            poll_interval_ms=self.poll_interval_ms,
        )
        return self

    def release(self) -> None:
        if self._fd is not None:
            release_file_lock(self._fd)
            self._fd = None

    def __enter__(self) -> "FileLock":
        return self.acquire()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release()


def with_file_lock(
    lock_path: str,
    fn: Any,
    *,
    retries: dict[str, Any] | None = None,
    stale: int | None = None,
):
    lock = FileLock(lock_path)
    return lock(fn) if callable(fn) else lock


class FileLockManager:
    def __init__(self, lock_dir: str | None = None):
        self.lock_dir = lock_dir or os.path.join(tempfile.gettempdir(), "openclaw-locks")
        os.makedirs(self.lock_dir, exist_ok=True)

    def _lock_path(self, name: str) -> str:
        safe_name = hashlib.sha256(name.encode()).hexdigest()[:16]
        return os.path.join(self.lock_dir, f"{safe_name}.lock")

    def acquire(self, name: str, timeout_ms: int = 30000) -> FileLock:
        return FileLock(self._lock_path(name), timeout_ms=timeout_ms).acquire()

    def release(self, name: str) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
