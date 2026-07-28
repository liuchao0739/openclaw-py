from __future__ import annotations

from typing import Any

from openclaw.commands.channels._helpers import _format_docs_link
from openclaw.commands.channels.shared import (
    append_base_url_bit,
    append_enabled_configured_linked_bits,
    append_mode_bit,
    append_token_source_bits,
    build_channel_account_line,
)


async def format_config_channels_status_lines(
    cfg: dict[str, Any],
    meta: dict[str, Any] | None = None,
    opts: dict[str, Any] | None = None,
) -> list[str]:
    lines: list[str] = []
    fallback_reason = (opts or {}).get("fallbackReason", "Gateway not reachable; showing config-only status.")
    lines.append(f"\x1b[33m{fallback_reason}\x1b[39m")

    if meta:
        if meta.get("path"):
            lines.append(f"Config: {meta['path']}")
        if meta.get("mode"):
            lines.append(f"Mode: {meta['mode']}")
        if meta.get("path") or meta.get("mode"):
            lines.append("")

    lines.append("")
    lines.append(f"\x1b[33mTip: {_format_docs_link('/cli#status', 'status --deep')} adds gateway health probes to status output.\x1b[39m")
    return lines
