from __future__ import annotations

import json
import os
import sqlite3
import time
from typing import Any, Dict, List, Optional


def _ensure_directory(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {key: row[key] for key in row.keys()}


class EmbeddingStorage:
    def __init__(self, db_path: str):
        self._db_path = db_path
        _ensure_directory(os.path.dirname(db_path))
        self._init_schema()

    def _init_schema(self) -> None:
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    id TEXT PRIMARY KEY,
                    text TEXT NOT NULL,
                    embedding BLOB,
                    dimensions INTEGER NOT NULL,
                    model TEXT,
                    session_key TEXT,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_embeddings_session
                ON embeddings(session_key)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_embeddings_model
                ON embeddings(model)
            """)
            conn.commit()
        finally:
            conn.close()

    def store(
        self,
        entry_id: str,
        text: str,
        embedding: List[float],
        dimensions: int,
        model: Optional[str] = None,
        session_key: Optional[str] = None,
    ) -> None:
        now = int(time.time() * 1000)
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute(
                """INSERT INTO embeddings
                   (id, text, embedding, dimensions, model, session_key, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET
                       text=excluded.text,
                       embedding=excluded.embedding,
                       dimensions=excluded.dimensions,
                       model=excluded.model,
                       session_key=excluded.session_key,
                       updated_at=excluded.updated_at
                """,
                (
                    entry_id,
                    text,
                    json.dumps(embedding).encode("utf-8"),
                    dimensions,
                    model,
                    session_key,
                    now,
                    now,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get(self, entry_id: str) -> Optional[Dict[str, Any]]:
        conn = sqlite3.connect(self._db_path)
        try:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM embeddings WHERE id = ?", (entry_id,)
            ).fetchone()
            if row:
                result = _row_to_dict(row)
                result["embedding"] = json.loads(result["embedding"])
                return result
            return None
        finally:
            conn.close()

    def delete(self, entry_id: str) -> bool:
        conn = sqlite3.connect(self._db_path)
        try:
            cursor = conn.execute("DELETE FROM embeddings WHERE id = ?", (entry_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def list_by_session(self, session_key: str, limit: int = 100) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self._db_path)
        try:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM embeddings WHERE session_key = ? ORDER BY updated_at DESC LIMIT ?",
                (session_key, limit),
            ).fetchall()
            results = []
            for row in rows:
                entry = _row_to_dict(row)
                entry["embedding"] = json.loads(entry["embedding"])
                results.append(entry)
            return results
        finally:
            conn.close()

    def clear_session(self, session_key: str) -> int:
        conn = sqlite3.connect(self._db_path)
        try:
            cursor = conn.execute(
                "DELETE FROM embeddings WHERE session_key = ?", (session_key,)
            )
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()

    def count(self) -> int:
        conn = sqlite3.connect(self._db_path)
        try:
            row = conn.execute("SELECT COUNT(*) FROM embeddings").fetchone()
            return row[0] if row else 0
        finally:
            conn.close()
