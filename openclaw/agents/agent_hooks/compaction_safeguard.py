"""Compaction safeguard extension (full summarization pipeline deferred to later tasks)."""

from __future__ import annotations

from openclaw.agents.sessions import ExtensionAPI


def register_compaction_safeguard_extension(api: ExtensionAPI) -> None:
    """Placeholder until compaction, plugins, and session compact workflow are ported."""

    def on_compact(_event: object, _ctx: object) -> None:
        return None

    if hasattr(api, "on"):
        try:
            api.on("compact", on_compact)
        except TypeError:
            pass