"""Gmail watcher error helpers classify watcher startup and runtime failures.

Mirrors src/hooks/gmail-watcher-errors.ts.
"""

from __future__ import annotations

import re

_ADDRESS_IN_USE_RE = re.compile(r"address already in use|EADDRINUSE", re.IGNORECASE)


def is_address_in_use_error(line: str) -> bool:
    """Detect watcher startup failures caused by an occupied bind port."""
    return bool(_ADDRESS_IN_USE_RE.search(line))
