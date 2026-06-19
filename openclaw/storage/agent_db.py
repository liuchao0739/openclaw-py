"""Per-agent SQLite database."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import MetaData, create_engine
from sqlalchemy.engine import Engine


def agent_db_path(state_dir: str, agent_id: str) -> Path:
    return Path(state_dir) / "agents" / agent_id / "agent" / "openclaw-agent.sqlite"


def init_agent_db(state_dir: str, agent_id: str) -> Engine:
    db_path = agent_db_path(state_dir, agent_id)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{db_path}")
    MetaData().create_all(engine)
    return engine
