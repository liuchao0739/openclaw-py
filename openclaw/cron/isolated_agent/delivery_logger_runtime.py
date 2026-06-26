"""Runtime logging seam for isolated-agent delivery tests.

Mirrors src/cron/isolated-agent/delivery-logger.runtime.ts — a barrel
re-export of logger helpers. Provides stub implementations that print to
stderr, matching the original's loose contract.
"""

from __future__ import annotations

import sys
from typing import Any


def log_error(message: str, *args: Any) -> None:
    """Log an error message to stderr."""
    parts = [message] + [str(a) for a in args]
    sys.stderr.write(" ".join(parts) + "\n")


def log_warn(message: str, *args: Any) -> None:
    """Log a warning message to stderr."""
    parts = [message] + [str(a) for a in args]
    sys.stderr.write(" ".join(parts) + "\n")
