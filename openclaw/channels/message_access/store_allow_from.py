"""Read pairing-store allowlist entries for direct-message policy."""

from __future__ import annotations

from typing import Any, Callable


async def read_channel_ingress_store_allow_from_for_dm_policy(
    provider: str,
    account_id: str,
    dm_policy: str | None = None,
    should_read: bool | None = None,
    read_store: Callable[[str, str], Any] | None = None,
) -> list[str]:
    """Read pairing-store allowlist entries when a direct-message policy permits store fallback."""
    if should_read is False or dm_policy in ("allowlist", "open"):
        return []

    if read_store is None:
        # Pairing store loading deferred; return empty when unavailable
        try:
            from openclaw.pairing.pairing_store import read_channel_allow_from_store

            import os

            result = await read_channel_allow_from_store(provider, os.environ, account_id)
            return result if isinstance(result, list) else []
        except Exception:
            return []

    try:
        result = await read_store(provider, account_id)
        return result if isinstance(result, list) else []
    except Exception:
        return []
