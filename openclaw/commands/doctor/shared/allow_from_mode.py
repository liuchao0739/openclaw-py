"""Doctor helper for resolving channel-specific direct-message allowlist semantics."""

from __future__ import annotations

from typing import Literal

AllowFromMode = Literal["strict", "permissive", "open"]


def resolve_allow_from_mode(channel_name: str) -> AllowFromMode:
    """Return the allowFrom interpretation mode advertised by a channel's doctor metadata."""
    try:
        from openclaw.commands.doctor.channel_capabilities import get_doctor_channel_capabilities

        caps = get_doctor_channel_capabilities(channel_name)
        return caps.get("dmAllowFromMode", "strict")
    except Exception:
        return "strict"
