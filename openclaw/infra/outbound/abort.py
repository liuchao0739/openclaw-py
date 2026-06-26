"""Abort helpers for async cancellation checkpoints.

Mirrors src/infra/outbound/abort.ts.
"""

from __future__ import annotations

import asyncio
from typing import Any


def throw_if_aborted(abort_signal: Any = None) -> None:
    """Throw an AbortError if the given signal has been aborted.

    Use at async checkpoints to support cancellation.
    """
    if abort_signal is None:
        return
    aborted = getattr(abort_signal, "aborted", False)
    if aborted:
        err = asyncio.CancelledError("Operation aborted")
        raise err
