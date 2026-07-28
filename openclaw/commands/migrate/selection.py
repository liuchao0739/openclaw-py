from __future__ import annotations

from typing import Any


def _build_selection_prompt(providers: list[dict[str, Any]]) -> str:
    lines = ["Available providers:"]
    for i, provider in enumerate(providers, 1):
        supported = "✓" if provider.get("supported") else "✗"
        lines.append(f"  {i}. {provider.get('name', 'unknown')} [{supported}] {provider.get('description', '')}")
    lines.append("")
    lines.append("Select a provider to migrate from:")
    return "\n".join(lines)


def select_provider_interactive(
    providers: list[dict[str, Any]],
    runtime: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    rt = runtime or {}
    if rt.get("log"):
        rt["log"](_build_selection_prompt(providers))
    return None


def auto_select_provider(
    provider_id: str,
    providers: list[dict[str, Any]],
) -> dict[str, Any] | None:
    for provider in providers:
        if provider.get("id") == provider_id:
            return provider
    return None
