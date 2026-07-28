"""PID liveness helpers check whether process ids still refer to active processes."""

from __future__ import annotations

import os
import signal
import platform
from typing import Any


def _is_valid_pid(pid: int) -> bool:
    return isinstance(pid, int) and pid > 0


def _is_zombie_process(pid: int) -> bool:
    if platform.system() != "Linux":
        return False
    try:
        with open(f"/proc/{pid}/status", "r") as f:
            status = f.read()
        import re
        match = re.search(r"^State:\s+(\S)", status, re.MULTILINE)
        if match:
            return match.group(1) == "Z"
    except (IOError, OSError):
        pass
    return False


def is_pid_alive(pid: int) -> bool:
    if not _is_valid_pid(pid):
        return False
    try:
        os.kill(pid, 0)
    except (OSError, ProcessLookupError):
        return False
    if _is_zombie_process(pid):
        return False
    return True


def is_pid_definitely_dead(pid: int) -> bool:
    if not _is_valid_pid(pid):
        return True
    try:
        os.kill(pid, 0)
    except (OSError, ProcessLookupError) as err:
        import errno
        if hasattr(err, 'errno') and err.errno == errno.ESRCH:
            return True
    return _is_zombie_process(pid)


def get_process_start_time(pid: int) -> int | None:
    if platform.system() != "Linux":
        return None
    if not _is_valid_pid(pid):
        return None
    try:
        with open(f"/proc/{pid}/stat", "r") as f:
            stat = f.read()
        comm_end = stat.rfind(")")
        if comm_end < 0:
            return None
        after_comm = stat[comm_end + 1:].lstrip()
        fields = after_comm.split()
        starttime = int(fields[19])
        return starttime if starttime >= 0 else None
    except (IOError, OSError, ValueError, IndexError):
        return None
