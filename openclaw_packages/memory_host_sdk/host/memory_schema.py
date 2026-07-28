from __future__ import annotations

import sqlite3
from typing import Optional

from .error_utils import format_error_message

MEMORY_INDEX_META_TABLE = "memory_index_meta"
MEMORY_INDEX_SOURCES_TABLE = "memory_index_sources"
MEMORY_INDEX_CHUNKS_TABLE = "memory_index_chunks"
MEMORY_EMBEDDING_CACHE_TABLE = "memory_embedding_cache"
MEMORY_INDEX_STATE_TABLE = "memory_index_state"
MEMORY_INDEX_FTS_TABLE = "memory_index_chunks_fts"
MEMORY_INDEX_VECTOR_TABLE = "memory_index_chunks_vec"

LEGACY_MEMORY_INDEX_TRIGGERS = [
    "memory_files_revision_after_insert",
    "memory_files_revision_after_update",
    "memory_files_revision_after_delete",
    "memory_chunks_revision_after_insert",
    "memory_chunks_revision_after_update",
    "memory_chunks_revision_after_delete",
]

MEMORY_INDEX_SOURCE_COLUMNS = ["path", "source", "hash", "mtime", "size"]


def _table_columns(conn: sqlite3.Connection, table_name: str, schema: str = "main") -> set:
    cursor = conn.execute(f"PRAGMA {schema}.table_info({table_name})")
    return {row[1] for row in cursor.fetchall()}


def _table_has_exact_columns(conn: sqlite3.Connection, table_name: str, expected: list, schema: str = "main") -> bool:
    columns = _table_columns(conn, table_name, schema)
    return len(columns) == len(expected) and all(col in columns for col in expected)


def _table_primary_key_columns(conn: sqlite3.Connection, table_name: str) -> list:
    cursor = conn.execute(f"PRAGMA table_info({table_name})")
    rows = cursor.fetchall()
    pk_rows = [(row[1], row[5]) for row in rows if isinstance(row[5], int) and row[5] > 0]
    pk_rows.sort(key=lambda x: x[1])
    return [col for col, _ in pk_rows]


def _table_has_primary_key(conn: sqlite3.Connection, table_name: str, expected_columns: list) -> bool:
    columns = _table_primary_key_columns(conn, table_name)
    return len(columns) == len(expected_columns) and columns == expected_columns


def _has_legacy_memory_index_tables(conn: sqlite3.Connection, schema: str = "main") -> bool:
    return (
        _table_has_exact_columns(conn, "meta", ["key", "value"], schema)
        and _table_has_exact_columns(conn, "files", ["path", "source", "hash", "mtime", "size"], schema)
        and _table_has_exact_columns(
            conn, "chunks",
            ["id", "path", "source", "start_line", "end_line", "hash", "model", "text", "embedding", "updated_at"],
            schema,
        )
    )


def _has_legacy_embedding_cache_table(conn: sqlite3.Connection, schema: str = "main") -> bool:
    return _table_has_exact_columns(
        conn, "embedding_cache",
        ["provider", "model", "provider_key", "hash", "embedding", "dims", "updated_at"],
        schema,
    )


def _migrate_canonical_memory_index_sources_primary_key(conn: sqlite3.Connection) -> None:
    if (
        not _table_has_exact_columns(conn, MEMORY_INDEX_SOURCES_TABLE, MEMORY_INDEX_SOURCE_COLUMNS)
        or _table_has_primary_key(conn, MEMORY_INDEX_SOURCES_TABLE, ["path", "source"])
    ):
        return
    if not _table_has_primary_key(conn, MEMORY_INDEX_SOURCES_TABLE, ["path"]):
        return

    try:
        conn.execute("SAVEPOINT migrate_memory_index_sources_primary_key")
        conn.execute(f"""
            DROP TRIGGER IF EXISTS memory_index_sources_revision_after_insert;
            DROP TRIGGER IF EXISTS memory_index_sources_revision_after_update;
            DROP TRIGGER IF EXISTS memory_index_sources_revision_after_delete;
            ALTER TABLE {MEMORY_INDEX_SOURCES_TABLE} RENAME TO memory_index_sources_path_pk_migration;
            CREATE TABLE {MEMORY_INDEX_SOURCES_TABLE} (
                path TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'memory',
                hash TEXT NOT NULL,
                mtime INTEGER NOT NULL,
                size INTEGER NOT NULL,
                PRIMARY KEY (path, source)
            );
            INSERT INTO {MEMORY_INDEX_SOURCES_TABLE} (path, source, hash, mtime, size)
            SELECT path, source, hash, mtime, size FROM memory_index_sources_path_pk_migration;
            DROP TABLE memory_index_sources_path_pk_migration;
            RELEASE migrate_memory_index_sources_primary_key;
        """)
    except Exception:
        conn.execute("ROLLBACK TO SAVEPOINT migrate_memory_index_sources_primary_key")
        conn.execute("RELEASE SAVEPOINT migrate_memory_index_sources_primary_key")
        raise


def _copy_legacy_memory_index_rows(conn: sqlite3.Connection, schema: str, preserved_embedding_cache_table: Optional[str] = None) -> None:
    conn.execute(f"""
        INSERT OR IGNORE INTO main.{MEMORY_INDEX_META_TABLE} (key, value)
        SELECT key, value FROM {schema}.meta;
        INSERT OR IGNORE INTO main.{MEMORY_INDEX_SOURCES_TABLE} (path, source, hash, mtime, size)
        SELECT path, source, hash, mtime, size FROM {schema}.files;
        INSERT OR IGNORE INTO main.{MEMORY_INDEX_CHUNKS_TABLE} (
            id, path, source, start_line, end_line, hash, model, text, embedding, updated_at
        )
        SELECT id, path, source, start_line, end_line, hash, model, text, embedding, updated_at
        FROM {schema}.chunks;
    """)
    if preserved_embedding_cache_table != "embedding_cache" and _has_legacy_embedding_cache_table(conn, schema):
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS main.{MEMORY_EMBEDDING_CACHE_TABLE} (
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                provider_key TEXT NOT NULL,
                hash TEXT NOT NULL,
                embedding TEXT NOT NULL,
                dims INTEGER,
                updated_at INTEGER NOT NULL,
                PRIMARY KEY (provider, model, provider_key, hash)
            );
            INSERT OR IGNORE INTO main.{MEMORY_EMBEDDING_CACHE_TABLE} (
                provider, model, provider_key, hash, embedding, dims, updated_at
            )
            SELECT provider, model, provider_key, hash, embedding, dims, updated_at
            FROM {schema}.embedding_cache;
        """)


def _migrate_legacy_memory_index_tables(conn: sqlite3.Connection, preserved_embedding_cache_table: Optional[str] = None) -> None:
    if not _has_legacy_memory_index_tables(conn):
        return
    try:
        conn.execute("SAVEPOINT migrate_legacy_memory_index_tables")
        _copy_legacy_memory_index_rows(conn, "main", preserved_embedding_cache_table)
        if preserved_embedding_cache_table != "embedding_cache" and _has_legacy_embedding_cache_table(conn):
            conn.execute("DROP TABLE IF EXISTS embedding_cache")
        for trigger in LEGACY_MEMORY_INDEX_TRIGGERS:
            conn.execute(f"DROP TRIGGER IF EXISTS {trigger}")
        conn.execute("""
            DROP TABLE IF EXISTS chunks_fts;
            DROP TABLE IF EXISTS chunks;
            DROP TABLE IF EXISTS files;
            DROP TABLE IF EXISTS meta;
            RELEASE SAVEPOINT migrate_legacy_memory_index_tables;
        """)
    except Exception:
        conn.execute("ROLLBACK TO SAVEPOINT migrate_legacy_memory_index_tables")
        conn.execute("RELEASE SAVEPOINT migrate_legacy_memory_index_tables")
        raise


def create_memory_schema(conn: sqlite3.Connection) -> None:
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {MEMORY_INDEX_META_TABLE} (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS {MEMORY_INDEX_SOURCES_TABLE} (
            path TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'memory',
            hash TEXT NOT NULL,
            mtime INTEGER NOT NULL,
            size INTEGER NOT NULL,
            PRIMARY KEY (path, source)
        );
        CREATE TABLE IF NOT EXISTS {MEMORY_INDEX_CHUNKS_TABLE} (
            id TEXT PRIMARY KEY,
            path TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'memory',
            start_line INTEGER NOT NULL,
            end_line INTEGER NOT NULL,
            hash TEXT NOT NULL,
            model TEXT NOT NULL,
            text TEXT NOT NULL,
            embedding TEXT NOT NULL,
            updated_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS {MEMORY_INDEX_STATE_TABLE} (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            revision INTEGER NOT NULL
        );
        INSERT OR IGNORE INTO {MEMORY_INDEX_STATE_TABLE} (id, revision) VALUES (1, 0);
    """)
    conn.commit()


def ensure_memory_index_schema(
    db_path: str,
    cache_enabled: bool,
    fts_enabled: bool,
    embedding_cache_table: Optional[str] = None,
    fts_table: Optional[str] = None,
    fts_tokenizer: Optional[str] = None,
) -> dict:
    embedding_cache_table = embedding_cache_table or MEMORY_EMBEDDING_CACHE_TABLE
    fts_table = fts_table or MEMORY_INDEX_FTS_TABLE

    conn = sqlite3.connect(db_path)
    try:
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {MEMORY_INDEX_META_TABLE} (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS {MEMORY_INDEX_SOURCES_TABLE} (
                path TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'memory',
                hash TEXT NOT NULL,
                mtime INTEGER NOT NULL,
                size INTEGER NOT NULL,
                PRIMARY KEY (path, source)
            );
            CREATE TABLE IF NOT EXISTS {MEMORY_INDEX_CHUNKS_TABLE} (
                id TEXT PRIMARY KEY,
                path TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'memory',
                start_line INTEGER NOT NULL,
                end_line INTEGER NOT NULL,
                hash TEXT NOT NULL,
                model TEXT NOT NULL,
                text TEXT NOT NULL,
                embedding TEXT NOT NULL,
                updated_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS {MEMORY_INDEX_STATE_TABLE} (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                revision INTEGER NOT NULL
            );
            INSERT OR IGNORE INTO {MEMORY_INDEX_STATE_TABLE} (id, revision) VALUES (1, 0);
        """)

        _migrate_canonical_memory_index_sources_primary_key(conn)

        conn.execute(f"""
            CREATE TRIGGER IF NOT EXISTS memory_index_sources_revision_after_insert
            AFTER INSERT ON {MEMORY_INDEX_SOURCES_TABLE}
            BEGIN
                UPDATE {MEMORY_INDEX_STATE_TABLE} SET revision = revision + 1 WHERE id = 1;
            END;
            CREATE TRIGGER IF NOT EXISTS memory_index_sources_revision_after_update
            AFTER UPDATE ON {MEMORY_INDEX_SOURCES_TABLE}
            BEGIN
                UPDATE {MEMORY_INDEX_STATE_TABLE} SET revision = revision + 1 WHERE id = 1;
            END;
            CREATE TRIGGER IF NOT EXISTS memory_index_sources_revision_after_delete
            AFTER DELETE ON {MEMORY_INDEX_SOURCES_TABLE}
            BEGIN
                UPDATE {MEMORY_INDEX_STATE_TABLE} SET revision = revision + 1 WHERE id = 1;
            END;
            CREATE TRIGGER IF NOT EXISTS memory_index_chunks_revision_after_insert
            AFTER INSERT ON {MEMORY_INDEX_CHUNKS_TABLE}
            BEGIN
                UPDATE {MEMORY_INDEX_STATE_TABLE} SET revision = revision + 1 WHERE id = 1;
            END;
            CREATE TRIGGER IF NOT EXISTS memory_index_chunks_revision_after_update
            AFTER UPDATE ON {MEMORY_INDEX_CHUNKS_TABLE}
            BEGIN
                UPDATE {MEMORY_INDEX_STATE_TABLE} SET revision = revision + 1 WHERE id = 1;
            END;
            CREATE TRIGGER IF NOT EXISTS memory_index_chunks_revision_after_delete
            AFTER DELETE ON {MEMORY_INDEX_CHUNKS_TABLE}
            BEGIN
                UPDATE {MEMORY_INDEX_STATE_TABLE} SET revision = revision + 1 WHERE id = 1;
            END;
            CREATE INDEX IF NOT EXISTS idx_memory_index_sources_source
                ON {MEMORY_INDEX_SOURCES_TABLE}(source);
            CREATE INDEX IF NOT EXISTS idx_memory_index_chunks_path_source
                ON {MEMORY_INDEX_CHUNKS_TABLE}(path, source);
            CREATE INDEX IF NOT EXISTS idx_memory_index_chunks_path
                ON {MEMORY_INDEX_CHUNKS_TABLE}(path);
            CREATE INDEX IF NOT EXISTS idx_memory_index_chunks_source
                ON {MEMORY_INDEX_CHUNKS_TABLE}(source);
        """)

        _migrate_legacy_memory_index_tables(conn, embedding_cache_table)

        if cache_enabled:
            updated_at_index = "idx_memory_embedding_cache_updated_at" if embedding_cache_table == MEMORY_EMBEDDING_CACHE_TABLE else "idx_embedding_cache_updated_at"
            conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {embedding_cache_table} (
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    provider_key TEXT NOT NULL,
                    hash TEXT NOT NULL,
                    embedding TEXT NOT NULL,
                    dims INTEGER,
                    updated_at INTEGER NOT NULL,
                    PRIMARY KEY (provider, model, provider_key, hash)
                );
                CREATE INDEX IF NOT EXISTS {updated_at_index}
                    ON {embedding_cache_table}(updated_at);
            """)

        fts_available = False
        fts_error = None
        if fts_enabled:
            try:
                tokenizer_clause = f", tokenize='trigram case_sensitive 0'" if fts_tokenizer == "trigram" else ""
                conn.execute(f"""
                    CREATE VIRTUAL TABLE IF NOT EXISTS {fts_table} USING fts5(
                        text,
                        id UNINDEXED,
                        path UNINDEXED,
                        source UNINDEXED,
                        model UNINDEXED,
                        start_line UNINDEXED,
                        end_line UNINDEXED
                        {tokenizer_clause}
                    );
                """)
                conn.execute(f"""
                    INSERT INTO {fts_table} (text, id, path, source, model, start_line, end_line)
                    SELECT text, id, path, source, model, start_line, end_line
                    FROM {MEMORY_INDEX_CHUNKS_TABLE}
                    WHERE NOT EXISTS (SELECT 1 FROM {fts_table} LIMIT 1);
                """)
                fts_available = True
            except Exception as err:
                fts_available = False
                fts_error = format_error_message(err)

        return {"ftsAvailable": fts_available, "ftsError": fts_error}
    finally:
        conn.close()
