from __future__ import annotations

from typing import Any


def search_plugins(query: str) -> list[dict]:
    return []


def format_search_results(results: list[dict]) -> str:
    if not results:
        return "No plugins found."
    lines: list[str] = []
    for r in results:
        name = r.get("name", "")
        desc = r.get("description", "")
        lines.append(f"  {name}: {desc}")
    return "
".join(lines)
