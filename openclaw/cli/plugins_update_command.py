from __future__ import annotations

from typing import Any


def update_plugin(name: str, version: str | None = None) -> dict:
    return {"name": name, "version": version, "updated": False}
