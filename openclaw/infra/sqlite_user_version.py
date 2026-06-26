"""SQLite user_version pragma reader.

Mirrors src/infra/sqlite-user-version.ts. Works with Python's sqlite3 module.
"""

from __future__ import annotations

import sqlite3
from typing import Any


def read_sqlite_user_version(db: sqlite3.Connection | Any) -> int:
    """Read the PRAGMA user_version from a SQLite database connection."""
    cursor = db.execute("PRAGMA user_version")
    row = cursor.fetchone()
    if row is None:
        return 0
    return int(row[0]) if row[0] is not None else 0
