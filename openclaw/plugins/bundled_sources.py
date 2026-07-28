from __future__ import annotations

from typing import Any


def resolve_bundled_plugin_ids() -> list[str]:
    return [
        "agent-compat",
        "agent-runtime",
        "agent-session",
        "code-tools",
        "web-search",
        "image-gen",
        "speech",
    ]


def is_bundled_plugin(plugin_id: str) -> bool:
    return plugin_id in resolve_bundled_plugin_ids()


def resolve_bundled_sources(plugin_id: str) -> list[str]:
    if is_bundled_plugin(plugin_id):
        return ["builtin"]
    return []
