from __future__ import annotations

from typing import Any

from openclaw.commands.channels._helpers import (
    _format_cli_command,
    _format_unknown_channel_message,
    _normalize_lowercase_string_or_empty,
    _normalize_optional_string,
)
from openclaw.commands.channels.shared import format_channel_account_label

CHANNEL_CAPABILITIES_TIMEOUT_MAX_MS = 30_000


def _resolve_channel_capabilities_timeout_ms(timeout_ms: int) -> int:
    return min(timeout_ms, CHANNEL_CAPABILITIES_TIMEOUT_MAX_MS)


def _format_support(capabilities: dict[str, Any] | None) -> str:
    if not capabilities:
        return "unknown"
    bits: list[str] = []
    chat_types = capabilities.get("chatTypes") or []
    if chat_types:
        bits.append(f"chatTypes={','.join(str(t) for t in chat_types)}")
    for feature in ["polls", "reactions", "edit", "unsend", "reply", "effects",
                    "groupManagement", "threads", "media", "nativeCommands", "blockStreaming"]:
        if capabilities.get(feature):
            bits.append(feature)
    return " ".join(bits) if bits else "none"


def _format_generic_probe_lines(probe: Any) -> list[dict[str, Any]]:
    if not probe or not isinstance(probe, dict):
        return []
    ok = probe.get("ok")
    if ok is True:
        return [{"text": "Probe: ok"}]
    if ok is False:
        error = f" ({probe.get('error')})" if probe.get("error") else ""
        return [{"text": f"Probe: failed{error}", "tone": "error"}]
    return []


def _render_display_line(line: dict[str, Any]) -> str:
    tone = line.get("tone")
    text = line.get("text", "")
    if tone == "muted":
        return f"\x1b[33m{text}\x1b[39m"
    if tone == "success":
        return f"\x1b[32m{text}\x1b[39m"
    if tone == "warn":
        return f"\x1b[33m{text}\x1b[39m"
    if tone == "error":
        return f"\x1b[31m{text}\x1b[39m"
    return text


async def channels_capabilities_command(
    opts: dict[str, Any],
    runtime: dict[str, Any] | None = None,
) -> None:
    rt = runtime or {}
    channel = _normalize_lowercase_string_or_empty(opts.get("channel"))
    target = _normalize_optional_string(opts.get("target")) or ""
    json_output = opts.get("json", False)

    if opts.get("account") and (not channel or channel == "all"):
        if rt.get("error"):
            rt["error"]("--account requires a specific --channel.")
        if rt.get("exit"):
            rt["exit"](1)
        return

    if target and (not channel or channel == "all"):
        if rt.get("error"):
            rt["error"]("--target requires a specific --channel.")
        if rt.get("exit"):
            rt["exit"](1)
        return

    if json_output:
        if rt.get("writeJson"):
            rt["writeJson"](rt, {"channels": []})
        return

    if not channel or channel == "all":
        if rt.get("log"):
            rt["log"]("No configured channel capabilities found.")
        return

    if rt.get("error"):
        rt["error"](_format_unknown_channel_message(channel))
    if rt.get("exit"):
        rt["exit"](1)
