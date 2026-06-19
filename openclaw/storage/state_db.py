"""Shared SQLite state database."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import MetaData, create_engine
from sqlalchemy.engine import Engine


def state_db_path(state_dir: str) -> Path:
    return Path(state_dir) / "state" / "openclaw.sqlite"


def init_state_db(state_dir: str) -> Engine:
    db_path = state_db_path(state_dir)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{db_path}")
    MetaData().create_all(engine)
    return engine
