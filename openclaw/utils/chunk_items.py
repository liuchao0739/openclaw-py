from __future__ import annotations

from typing import TypeVar

T = TypeVar("T")


def chunk_items(items: list[T], size: int) -> list[list[T]]:
    if size <= 0:
        return [list(items)]
    rows: list[list[T]] = []
    for i in range(0, len(items), size):
        rows.append(items[i : i + size])
    return rows
