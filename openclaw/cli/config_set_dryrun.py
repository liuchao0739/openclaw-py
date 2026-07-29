from __future__ import annotations

from typing import Any


def format_dry_run_output(key: str, old_value: Any, new_value: Any) -> str:
    return f"[dry-run] {key}: {old_value!r} -> {new_value!r}"


def is_dry_run(argv: list[str]) -> bool:
    return "--dry-run" in argv
