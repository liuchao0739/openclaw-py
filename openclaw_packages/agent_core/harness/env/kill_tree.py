from __future__ import annotations

import os
import signal
import subprocess
import threading
import time
from typing import Any, Literal

DEFAULT_GRACE_MS = 3000
MAX_GRACE_MS = 60_000


def _normalize_grace_ms(value: int | None) -> int:
    if value is None:
        return DEFAULT_GRACE_MS
    if not isinstance(value, int):
        return DEFAULT_GRACE_MS
    return max(0, min(MAX_GRACE_MS, value))


def _is_process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def _signal_process_tree_unix(
    pid: int,
    sig: int,
    use_group_kill: bool,
) -> None:
    if use_group_kill:
        try:
            os.kill(-pid, sig)
            return
        except (OSError, ProcessLookupError):
            pass
    try:
        os.kill(pid, sig)
    except (OSError, ProcessLookupError):
        pass


def _run_taskkill(args: list[str]) -> None:
    try:
        subprocess.Popen(
            ["taskkill", *args],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except Exception:
        pass


def _signal_process_tree_windows(
    pid: int,
    sig: Literal["SIGTERM", "SIGKILL"],
) -> None:
    if sig == "SIGKILL":
        args = ["/F", "/T", "/PID", str(pid)]
    else:
        args = ["/T", "/PID", str(pid)]
    _run_taskkill(args)


def _kill_process_tree_windows(pid: int, grace_ms: int) -> None:
    _signal_process_tree_windows(pid, "SIGTERM")

    def _wait_and_kill() -> None:
        if not _is_process_alive(pid):
            return
        _signal_process_tree_windows(pid, "SIGKILL")

    threading.Timer(grace_ms / 1000.0, _wait_and_kill).start()


def kill_process_tree(pid: int, opts: dict[str, Any] | None = None) -> None:
    if not isinstance(pid, int) or pid <= 0:
        return
    opts = opts or {}
    if os.name == "nt":
        if opts.get("force") is True:
            _signal_process_tree_windows(pid, "SIGKILL")
            return
        grace_ms = _normalize_grace_ms(opts.get("graceMs"))
        _kill_process_tree_windows(pid, grace_ms)
        return

    use_group_kill = opts.get("detached", True) is not False
    if opts.get("force") is True:
        _signal_process_tree_unix(pid, signal.SIGKILL, use_group_kill)
        return
    grace_ms = _normalize_grace_ms(opts.get("graceMs"))
    _signal_process_tree_unix(pid, signal.SIGTERM, use_group_kill)

    def _wait_and_kill() -> None:
        still_alive = (
            _is_process_alive(-pid) or _is_process_alive(pid)
            if use_group_kill
            else _is_process_alive(pid)
        )
        if not still_alive:
            return
        _signal_process_tree_unix(pid, signal.SIGKILL, use_group_kill)

    threading.Timer(grace_ms / 1000.0, _wait_and_kill).start()


def signal_process_tree(
    pid: int,
    sig: Literal["SIGTERM", "SIGKILL"],
    opts: dict[str, Any] | None = None,
) -> None:
    if not isinstance(pid, int) or pid <= 0:
        return
    opts = opts or {}
    if os.name == "nt":
        _signal_process_tree_windows(pid, sig)
        return
    _signal_process_tree_unix(
        pid,
        signal.SIGTERM if sig == "SIGTERM" else signal.SIGKILL,
        opts.get("detached", True) is not False,
    )
