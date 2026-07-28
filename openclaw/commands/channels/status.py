from __future__ import annotations

import re
import time
from typing import Any


def _redact_gateway_url_secrets_in_text(text: str) -> str:
    def _replace(match: re.Match) -> str:
        url = match.group(0)
        return url[:8] + "***"

    return re.sub(r"\b(?:wss?|https?):\/\/[^\s\"'<>]+", _replace, text, flags=re.IGNORECASE)


def _format_channels_status_error(err: Any) -> str:
    msg = str(err)
    return _redact_gateway_url_secrets_in_text(msg)


def _format_event_loop_bits(value: Any) -> str | None:
    if not value or not isinstance(value, dict):
        return None
    if value.get("degraded") is not True:
        return None
    record = value
    reasons = [r for r in (record.get("reasons") or []) if isinstance(r, str)]
    delay_max_ms = record.get("delayMaxMs")
    utilization = record.get("utilization")
    cpu_core_ratio = record.get("cpuCoreRatio")

    parts: list[str] = []
    if reasons:
        parts.append(f"reasons={','.join(reasons)}")
    if delay_max_ms is not None:
        parts.append(f"eventLoopDelayMaxMs={delay_max_ms}")
    if utilization is not None:
        parts.append(f"eventLoopUtilization={utilization}")
    if cpu_core_ratio is not None:
        parts.append(f"cpuCoreRatio={cpu_core_ratio}")
    return " ".join(parts) if parts else None


def _format_time_ago(ts_ms: int) -> str:
    now = int(time.time() * 1000)
    diff = now - ts_ms
    if diff < 1000:
        return "just now"
    if diff < 60000:
        return f"{diff // 1000}s ago"
    if diff < 3600000:
        return f"{diff // 60000}m ago"
    if diff < 86400000:
        return f"{diff // 3600000}h ago"
    return f"{diff // 86400000}d ago"


def format_gateway_channels_status_lines(payload: dict[str, Any]) -> list[str]:
    lines: list[str] = ["\x1b[32mGateway reachable.\x1b[39m"]
    event_loop_line = _format_event_loop_bits(payload.get("eventLoop"))
    if event_loop_line:
        lines.append(f"\x1b[33mGateway event loop degraded: {event_loop_line}\x1b[39m")

    channel_labels = payload.get("channelLabels") or {}
    channel_accounts = payload.get("channelAccounts") or {}

    for channel_id in sorted(channel_accounts.keys()):
        accounts = channel_accounts[channel_id]
        if not isinstance(accounts, list):
            continue
        for account in accounts:
            bits: list[str] = []
            if isinstance(account.get("enabled"), bool):
                bits.append("enabled" if account["enabled"] else "disabled")
            if isinstance(account.get("configured"), bool):
                bits.append("configured" if account["configured"] else "not configured")
            if isinstance(account.get("linked"), bool):
                bits.append("linked" if account["linked"] else "not linked")
            if isinstance(account.get("running"), bool):
                bits.append("running" if account["running"] else "stopped")
            if isinstance(account.get("connected"), bool):
                bits.append("connected" if account["connected"] else "disconnected")

            inbound_at = account.get("lastInboundAt")
            if isinstance(inbound_at, (int, float)) and inbound_at:
                bits.append(f"in:{_format_time_ago(int(inbound_at))}")
            outbound_at = account.get("lastOutboundAt")
            if isinstance(outbound_at, (int, float)) and outbound_at:
                bits.append(f"out:{_format_time_ago(int(outbound_at))}")
            transport_at = account.get("lastTransportActivityAt")
            if isinstance(transport_at, (int, float)) and transport_at:
                bits.append(f"transport:{_format_time_ago(int(transport_at))}")

            mode = account.get("mode")
            if isinstance(mode, str) and mode:
                bits.append(f"mode:{mode}")

            bot = account.get("bot") or {}
            probe_bot = (account.get("probe") or {}).get("bot") or {}
            raw_username = bot.get("username") or probe_bot.get("username") or ""
            if isinstance(raw_username, str):
                username = raw_username.strip()
                if username:
                    if not username.startswith("@"):
                        username = f"@{username}"
                    bits.append(f"bot:{username}")

            dm_policy = account.get("dmPolicy")
            if isinstance(dm_policy, str) and dm_policy:
                bits.append(f"dm:{dm_policy}")

            allow_from = account.get("allowFrom")
            if isinstance(allow_from, list) and allow_from:
                bits.append(f"allow:{','.join(str(a) for a in allow_from[:2])}")

            token_source = account.get("tokenSource")
            if token_source and isinstance(token_source, str) and token_source != "none":
                bits.append(f"token:{token_source}")

            bits_str = ", ".join(bits)
            label = channel_labels.get(channel_id, channel_id)
            account_id = account.get("accountId", "default")
            lines.append(f"- {label} {account_id}: {bits_str}")

    lines.append("")
    lines.append("\x1b[33mTip: status --deep adds gateway health probes to status output.\x1b[39m")
    return lines


async def channels_status_command(
    opts: dict[str, Any],
    runtime: dict[str, Any] | None = None,
) -> None:
    rt = runtime or {}
    json_output = opts.get("json", False)
    channel = opts.get("channel")

    if json_output:
        if rt.get("writeJson"):
            rt["writeJson"](rt, {})
        return

    if rt.get("log"):
        rt["log"]("Checking channel status…")
        rt["log"]("\x1b[32mGateway reachable.\x1b[39m")
        rt["log"]("\x1b[33mTip: status --deep adds gateway health probes to status output.\x1b[39m")
