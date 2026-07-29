from __future__ import annotations

from typing import Any


def install_plugin(name: str, version: str | None = None) -> dict:
    return {"name": name, "version": version, "installed": False}


def resolve_install_source(name: str) -> str:
    return name
