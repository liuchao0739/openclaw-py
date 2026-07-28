from __future__ import annotations

import os
import sqlite3
import time
from typing import Any, Dict, List, Optional

from .host.config_utils import normalize_agent_id, resolve_state_dir
from .host.error_utils import format_error_message


class MemoryStorage:
    def __init__(self, db_path: str):
        self._db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
            self._conn = sqlite3.connect(self._db_path)
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=NORMAL")
            self._init_tables()
        return self._conn

    def _init_tables(self) -> None:
        conn = self._conn
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memory_index_chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                chunk_text TEXT NOT NULL,
                embedding_id TEXT,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                UNIQUE(file_path, chunk_index)
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_chunks_file
            ON memory_index_chunks(file_path)
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memory_index_files (
                file_path TEXT PRIMARY KEY,
                indexed_at INTEGER NOT NULL,
                hash TEXT,
                chunk_count INTEGER DEFAULT 0
            )
        """)
        conn.commit()

    def upsert_chunk(
        self,
        file_path: str,
        chunk_index: int,
        chunk_text: str,
        embedding_id: Optional[str] = None,
    ) -> None:
        now = int(time.time() * 1000)
        conn = self._get_conn()
        conn.execute(
            """INSERT INTO memory_index_chunks
               (file_path, chunk_index, chunk_text, embedding_id, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(file_path, chunk_index) DO UPDATE SET
                   chunk_text=excluded.chunk_text,
                   embedding_id=excluded.embedding_id,
                   updated_at=excluded.updated_at
            """,
            (file_path, chunk_index, chunk_text, embedding_id, now, now),
        )
        conn.commit()

    def update_file_indexed(self, file_path: str, file_hash: Optional[str] = None, chunk_count: int = 0) -> None:
        now = int(time.time() * 1000)
        conn = self._get_conn()
        conn.execute(
            """INSERT INTO memory_index_files (file_path, indexed_at, hash, chunk_count)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(file_path) DO UPDATE SET
                   indexed_at=excluded.indexed_at,
                   hash=excluded.hash,
                   chunk_count=excluded.chunk_count
            """,
            (file_path, now, file_hash, chunk_count),
        )
        conn.commit()

    def list_indexed_files(self) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM memory_index_files ORDER BY indexed_at DESC").fetchall()
        return [dict(row) for row in rows]

    def get_chunks_for_file(self, file_path: str) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM memory_index_chunks WHERE file_path = ? ORDER BY chunk_index",
            (file_path,),
        ).fetchall()
        return [dict(row) for row in rows]

    def delete_file_chunks(self, file_path: str) -> None:
        conn = self._get_conn()
        conn.execute("DELETE FROM memory_index_chunks WHERE file_path = ?", (file_path,))
        conn.execute("DELETE FROM memory_index_files WHERE file_path = ?", (file_path,))
        conn.commit()

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None


def create_memory_storage(agent_id: str, state_dir: Optional[str] = None) -> MemoryStorage:
    normalized_agent_id = normalize_agent_id(agent_id)
    sd = state_dir or resolve_state_dir()
    db_path = os.path.join(sd, "agents", normalized_agent_id, "memory.db")
    return MemoryStorage(db_path)
