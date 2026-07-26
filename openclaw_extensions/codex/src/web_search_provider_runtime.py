"""Codex web search provider runtime."""

from __future__ import annotations

from typing import Any


async def execute_codex_web_search_provider_tool(
    ctx: dict[str, Any],
    args: dict[str, Any],
    execution_context: dict[str, Any],
    options: dict[str, Any] | None = None,
) -> Any:
    raise RuntimeError("Codex hosted web search runtime is not available in this environment")
