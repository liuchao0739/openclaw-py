from __future__ import annotations

from typing import Optional

DEFAULT_SQLITE_WAL_AUTOCHECKPOINT_PAGES = 1000
DEFAULT_SQLITE_WAL_CHECKPOINT_INTERVAL_MS = 60_000
DEFAULT_SQLITE_WAL_TRUNCATE_INTERVAL_MS = 3_600_000


def configure_sqlite_connection_pragmas(conn: object, options: Optional[dict] = None) -> None:
    import sqlite3
    if not isinstance(conn, sqlite3.Connection):
        return
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        if options and "busyTimeoutMs" in options:
            conn.execute(f"PRAGMA busy_timeout = {options['busyTimeoutMs']}")
    except Exception:
        pass


def configure_sqlite_wal_maintenance(conn: object, options: Optional[dict] = None) -> dict:
    configure_sqlite_connection_pragmas(conn, options)
    return {"connection": conn}
