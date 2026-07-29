from __future__ import annotations

from typing import Any, TypedDict


class DepSpec(TypedDict, total=False):
    name: str
    version: str
    optional: bool


class DepResolution(TypedDict, total=False):
    found: list[str]
    missing: list[str]
    errors: list[str]
