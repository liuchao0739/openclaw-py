from __future__ import annotations

from typing import Any

from openclaw.packages.normalization_core import normalize_optional_string


def resolve_npm_package_name(raw: str | None) -> str | None:
    return normalize_optional_string(raw)


def is_scoped_package(name: str) -> bool:
    return name.startswith("@")
