from __future__ import annotations

from typing import Any


def uninstall_plugin(name: str) -> dict:
    return {"name": name, "uninstalled": False}
