from __future__ import annotations

import hashlib
import json
import os
from typing import Any


PRIMARY_ROW_KEY = "primary"


def _resolve_agent_dir(agent_dir: str | None = None) -> str:
    if agent_dir:
        return os.path.expanduser(agent_dir)
    from openclaw.agents.agent_scope_config import resolve_default_agent_dir
    return resolve_default_agent_dir()


def _infer_agent_id_from_dir(agent_dir: str) -> str:
    normalized = os.path.normpath(agent_dir)
    basename = os.path.basename(normalized)
    if basename == "agent":
        parent = os.path.basename(os.path.dirname(normalized))
        if parent:
            return parent
    hash_val = hashlib.sha256(normalized.encode()).hexdigest()[:12]
    return f"custom-{hash_val}"


def _resolve_auth_profile_database_options(agent_dir: str | None = None) -> dict[str, Any]:
    dir_path = _resolve_agent_dir(agent_dir)
    from openclaw.agents.agent_dir_registry import resolve_registered_agent_id_for_dir
    agent_id = resolve_registered_agent_id_for_dir(dir_path)
    if not agent_id:
        agent_id = _infer_agent_id_from_dir(dir_path)
    return {
        "agentId": agent_id,
        "path": os.path.join(dir_path, "openclaw-agent.sqlite"),
    }


def resolve_auth_profile_database_path(agent_dir: str | None = None) -> str:
    return _resolve_auth_profile_database_options(agent_dir)["path"]


def _parse_json_cell(raw: Any) -> Any:
    if not raw:
        return None
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return None
    return raw


def read_persisted_auth_profile_store_raw(
    agent_dir: str | None = None,
    database: Any = None,
) -> Any:
    try:
        db_path = resolve_auth_profile_database_path(agent_dir)
        if not os.path.exists(db_path):
            return None
        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute(
                "SELECT store_json FROM auth_profile_store WHERE store_key = ?",
                (PRIMARY_ROW_KEY,),
            ).fetchone()
            if row:
                return _parse_json_cell(row["store_json"])
            return None
        finally:
            conn.close()
    except Exception:
        return None


def read_persisted_auth_profile_state_raw(
    agent_dir: str | None = None,
    database: Any = None,
) -> Any:
    try:
        db_path = resolve_auth_profile_database_path(agent_dir)
        if not os.path.exists(db_path):
            return None
        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute(
                "SELECT state_json FROM auth_profile_state WHERE state_key = ?",
                (PRIMARY_ROW_KEY,),
            ).fetchone()
            if row:
                return _parse_json_cell(row["state_json"])
            return None
        finally:
            conn.close()
    except Exception:
        return None


def write_persisted_auth_profile_store_raw(
    payload: Any,
    agent_dir: str | None = None,
    database: Any = None,
) -> None:
    db_path = resolve_auth_profile_database_path(agent_dir)
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    import sqlite3
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "INSERT OR REPLACE INTO auth_profile_store (store_key, store_json, updated_at) VALUES (?, ?, ?)",
            (PRIMARY_ROW_KEY, json.dumps(payload), int(__import__("time").time() * 1000)),
        )
        conn.commit()
    finally:
        conn.close()


def write_persisted_auth_profile_state_raw(
    payload: Any,
    agent_dir: str | None = None,
    database: Any = None,
) -> None:
    db_path = resolve_auth_profile_database_path(agent_dir)
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    import sqlite3
    conn = sqlite3.connect(db_path)
    try:
        if not payload:
            conn.execute(
                "DELETE FROM auth_profile_state WHERE state_key = ?",
                (PRIMARY_ROW_KEY,),
            )
        else:
            conn.execute(
                "INSERT OR REPLACE INTO auth_profile_state (state_key, state_json, updated_at) VALUES (?, ?, ?)",
                (PRIMARY_ROW_KEY, json.dumps(payload), int(__import__("time").time() * 1000)),
            )
        conn.commit()
    finally:
        conn.close()


def run_auth_profile_write_transaction(
    agent_dir: str | None,
    operation: Any,
) -> Any:
    db_path = resolve_auth_profile_database_path(agent_dir)
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    import sqlite3
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("BEGIN")
        result = operation(conn)
        conn.commit()
        return result
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def delete_persisted_auth_profile_store_raw(
    agent_dir: str | None = None,
    database: Any = None,
) -> None:
    db_path = resolve_auth_profile_database_path(agent_dir)
    import sqlite3
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "DELETE FROM auth_profile_store WHERE store_key = ?",
            (PRIMARY_ROW_KEY,),
        )
        conn.commit()
    finally:
        conn.close()
