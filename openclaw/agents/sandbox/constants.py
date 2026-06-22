"""Sandbox defaults and naming (paths resolved via openclaw.infra.paths when wired)."""

from __future__ import annotations

DEFAULT_SANDBOX_IMAGE = "openclaw-sandbox:bookworm-slim"
DEFAULT_SANDBOX_CONTAINER_PREFIX = "openclaw-sbx-"
DEFAULT_SANDBOX_WORKDIR = "/workspace"
DEFAULT_SANDBOX_IDLE_HOURS = 24
DEFAULT_SANDBOX_MAX_AGE_DAYS = 7

DEFAULT_TOOL_ALLOW: tuple[str, ...] = (
    "exec",
    "process",
    "read",
    "write",
    "edit",
    "apply_patch",
    "image",
    "sessions_list",
    "sessions_history",
    "sessions_send",
    "sessions_spawn",
    "sessions_yield",
    "subagents",
    "session_status",
)

# Channel tool names are denied in sandbox by default (aligned with TS CHANNEL_IDS docking).
DEFAULT_TOOL_DENY: tuple[str, ...] = (
    "browser",
    "canvas",
    "nodes",
    "cron",
    "gateway",
    "telegram",
    "discord",
    "slack",
    "signal",
    "imessage",
    "whatsapp",
    "line",
    "feishu",
    "googlechat",
)

DEFAULT_SANDBOX_BROWSER_IMAGE = "openclaw-sandbox-browser:bookworm-slim"
DEFAULT_SANDBOX_COMMON_IMAGE = "openclaw-sandbox-common:bookworm-slim"
SANDBOX_BROWSER_SECURITY_HASH_EPOCH = "2026-05-12-cdp-relay-auth"
SANDBOX_BROWSER_IMAGE_CONTRACT_EPOCH = "2026-05-12-cdp-relay-auth"

DEFAULT_SANDBOX_BROWSER_PREFIX = "openclaw-sbx-browser-"
DEFAULT_SANDBOX_BROWSER_NETWORK = "openclaw-sandbox-browser"
DEFAULT_SANDBOX_BROWSER_CDP_PORT = 9222
DEFAULT_SANDBOX_BROWSER_VNC_PORT = 5900
DEFAULT_SANDBOX_BROWSER_NOVNC_PORT = 6080
DEFAULT_SANDBOX_BROWSER_AUTOSTART_TIMEOUT_MS = 12_000

SANDBOX_AGENT_WORKSPACE_MOUNT = "/agent"