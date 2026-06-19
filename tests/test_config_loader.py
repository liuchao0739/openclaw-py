"""Tests for config loader."""

from __future__ import annotations

import json
from pathlib import Path

from openclaw.config.loader import load_config_file
from openclaw.config.models import OpenClawConfig


def test_load_config_file(tmp_path: Path) -> None:
    config_path = tmp_path / "openclaw.json"
    config_path.write_text(
        json.dumps({"gateway": {"port": 19999, "bind": "lan"}, "agents": {"defaults": {"model": "gpt-4"}}}),
        encoding="utf-8",
    )
    config = load_config_file(config_path)
    assert isinstance(config, OpenClawConfig)
    assert config.gateway is not None
    assert config.gateway.resolved_port() == 19999
    assert config.agents is not None
    assert config.agents.defaults is not None
    assert config.agents.defaults.model == "gpt-4"


def test_empty_config_defaults() -> None:
    config = OpenClawConfig()
    assert config.gateway is None
