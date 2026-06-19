"""Load and validate openclaw.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from openclaw.config.models import OpenClawConfig
from openclaw.infra.paths import resolve_config_path


def load_config_file(path: str | Path) -> OpenClawConfig:
    config_path = Path(path)
    raw: dict[str, Any] = json.loads(config_path.read_text(encoding="utf-8"))
    return OpenClawConfig.model_validate(raw)


def load_config(
    env: dict[str, str] | None = None,
    config_path: str | Path | None = None,
) -> OpenClawConfig:
    path = Path(config_path) if config_path else Path(resolve_config_path(env))
    if not path.exists():
        return OpenClawConfig()
    return load_config_file(path)
