"""Channel media limit resolver.

Combines account-scoped channel media limits with agent default limits.
"""

from __future__ import annotations

from typing import Any, Callable

MB = 1024 * 1024


def resolve_channel_media_max_bytes(
    cfg: dict[str, Any] | None,
    resolve_channel_limit_mb: Callable[[dict[str, Any], str], int | None],
    account_id: str | None = None,
) -> int | None:
    """Resolve channel media limit bytes from account-specific config or agent defaults."""
    account = (account_id or "default").strip() or "default"

    channel_limit = resolve_channel_limit_mb(cfg or {}, account)
    if channel_limit:
        return channel_limit * MB

    if cfg:
        agents = cfg.get("agents", {})
        if isinstance(agents, dict):
            defaults = agents.get("defaults", {})
            if isinstance(defaults, dict):
                media_max_mb = defaults.get("mediaMaxMb")
                if isinstance(media_max_mb, (int, float)) and media_max_mb > 0:
                    return int(media_max_mb * MB)

    return None
