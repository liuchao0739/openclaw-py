"""Armable idle watchdog for long-running channel transports."""

from __future__ import annotations

import threading
import time
from typing import Any, Callable


class ArmableStallWatchdog:
    """Watchdog that reports once when an armed transport goes idle."""

    def __init__(
        self,
        label: str,
        timeout_ms: int,
        on_timeout: Callable[[dict[str, int]], None],
        check_interval_ms: int | None = None,
    ) -> None:
        self._label = label
        self._timeout_ms = max(1, timeout_ms)
        default_check = min(5000, max(250, self._timeout_ms // 6))
        self._check_interval_ms = max(100, check_interval_ms or default_check)
        self._on_timeout = on_timeout

        self._armed = False
        self._stopped = False
        self._last_activity_at = time.time() * 1000
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()

    def arm(self, at_ms: float | None = None) -> None:
        with self._lock:
            if self._stopped:
                return
            self._last_activity_at = at_ms if at_ms is not None else time.time() * 1000
            self._armed = True
            self._ensure_timer()

    def touch(self, at_ms: float | None = None) -> None:
        with self._lock:
            if self._stopped:
                return
            self._last_activity_at = at_ms if at_ms is not None else time.time() * 1000

    def disarm(self) -> None:
        with self._lock:
            self._armed = False

    def stop(self) -> None:
        with self._lock:
            if self._stopped:
                return
            self._stopped = True
            self._armed = False
            self._clear_timer()

    def is_armed(self) -> bool:
        return self._armed

    def _ensure_timer(self) -> None:
        if self._timer is not None:
            return
        self._timer = threading.Timer(self._check_interval_ms / 1000.0, self._check)
        self._timer.daemon = True
        self._timer.start()

    def _clear_timer(self) -> None:
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

    def _check(self) -> None:
        with self._lock:
            if not self._armed or self._stopped:
                if not self._stopped:
                    self._timer = None
                return
            now = time.time() * 1000
            idle_ms = now - self._last_activity_at
            if idle_ms < self._timeout_ms:
                self._timer = None
                self._ensure_timer()
                return
            self._armed = False
            self._timer = None

        self._on_timeout({"idleMs": int(idle_ms), "timeoutMs": self._timeout_ms})


def create_armable_stall_watchdog(
    label: str,
    timeout_ms: int,
    on_timeout: Callable[[dict[str, int]], None],
    check_interval_ms: int | None = None,
) -> ArmableStallWatchdog:
    """Create a watchdog that reports once when an armed transport goes idle."""
    return ArmableStallWatchdog(label, timeout_ms, on_timeout, check_interval_ms)
