from __future__ import annotations

from typing import Any

ROOT_HELP_METADATA: dict[str, Any] = {
    "description": "OpenClaw - multi-channel AI gateway",
    "usage": "openclaw [command] [options]",
}


def get_root_help_metadata() -> dict:
    return dict(ROOT_HELP_METADATA)


def update_root_help_metadata(key: str, value: Any) -> None:
    ROOT_HELP_METADATA[key] = value
