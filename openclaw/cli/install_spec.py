from __future__ import annotations

from typing import Any, TypedDict


class InstallSpec(TypedDict, total=False):
    name: str
    version: str
    source: str
    target: str


def normalize_install_spec(raw: dict) -> InstallSpec:
    result: dict[str, Any] = {}
    if raw.get("name"):
        result["name"] = raw["name"]
    if raw.get("version"):
        result["version"] = raw["version"]
    if raw.get("source"):
        result["source"] = raw["source"]
    if raw.get("target"):
        result["target"] = raw["target"]
    return result
