from __future__ import annotations

import sqlite3
from typing import Optional

from .error_utils import format_error_message

_sqlite_wal_maintenance_by_db = {}


def require_node_sqlite() -> str:
    try:
        import sqlite3
        return "sqlite3"
    except ImportError as err:
        message = format_error_message(err)
        raise RuntimeError(
            f"SQLite support is unavailable in this Python runtime. {message}"
        )


def configure_memory_sqlite_wal_maintenance(
    db_path: str,
    options: Optional[dict] = None,
) -> dict:
    conn = sqlite3.connect(db_path)
    try:
        if options and "busyTimeoutMs" in options:
            conn.execute(f"PRAGMA busy_timeout = {options['busyTimeoutMs']}")
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return {"connection": conn, "path": db_path}
    except Exception:
        conn.close()
        raise


def close_memory_sqlite_wal_maintenance(db_path: str) -> bool:
    maintenance = _sqlite_wal_maintenance_by_db.pop(db_path, None)
    if not maintenance:
        return True
    try:
        maintenance["connection"].close()
        return True
    except Exception:
        return False
