from __future__ import annotations

from typing import Any


def inspect_plugin(name: str) -> dict:
    return {"name": name, "installed": False}


def format_plugin_inspect(info: dict) -> str:
    import json

    return json.dumps(info, indent=2)
