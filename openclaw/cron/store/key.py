"""Cron store key normalization for SQLite partitions.

Mirrors src/cron/store/key.ts.
"""

from __future__ import annotations

import os
from pathlib import Path


def cron_store_key(store_path: str) -> str:
    """Return the canonical per-file SQLite partition key for cron store rows."""
    return str(Path(store_path).resolve())
