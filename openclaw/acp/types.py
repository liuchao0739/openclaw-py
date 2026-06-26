"""ACP protocol helpers and OpenClaw agent identity metadata.

Mirrors src/acp/types.ts.
"""

from __future__ import annotations

from openclaw import __version__

ACP_AGENT_INFO = {
    "name": "openclaw-acp",
    "title": "OpenClaw ACP Gateway",
    "version": __version__,
}


def normalize_acp_provenance_mode(value: str | None) -> str:
    """Normalize an ACP provenance mode."""
    if not isinstance(value, str):
        return "off"
    normalized = value.strip().lower()
    if normalized in ("off", "none"):
        return "off"
    if normalized in ("on", "always", "enabled"):
        return "on"
    if normalized in ("auto", "automatic"):
        return "auto"
    return "off"
