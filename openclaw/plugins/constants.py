from __future__ import annotations

from typing import Any


PLUGIN_CONFIG_FILENAME = "openclaw.plugin.json"
PLUGIN_MANIFEST_FILENAME = "openclaw.plugin.json"
LEGACY_PLUGIN_MANIFEST_FILENAME = "plugin.json"
PLUGIN_WORKDIR = ".openclaw/plugins"

PLUGIN_COMPAT_DIR = ".openclaw/plugin-compat"
PLUGIN_MIGRATION_STATE_FILENAME = "plugin-migration-state.json"

PLUGIN_API_COMPAT_DIR = ".openclaw/plugin-api-compat"
PLUGIN_API_COMPAT_STATE_FILENAME = "plugin-api-compat-state.json"
PLUGIN_API_COMPAT_STATE_VERSION = 1

EXPERIMENTAL_PLUGIN_APIS: set[str] = {
    "agent:append-user-context",
    "agent:configure-session-start-meta",
    "agent:create-session-hooks",
    "agent:inject-hooks:read-only",
    "agent:list-session-tools",
    "agent:persist-session-provider-state",
    "agent:resolve-context-pruning-policy",
    "agent:resolve-profile-display-metadata",
    "agent:resolve-profile-order",
    "agent:resolve-profile-usage-stats",
    "agent:resolve-session-identity",
    "agent:resolve-session-provider-state",
    "agent:resolve-session-state",
    "agent:run-background-job",
    "agent:session-context-snapshot",
    "agent:update-session-provider-state",
}

BETA_PLUGIN_APIS: set[str] = {
    "agent:build-debug-session-envelope",
    "agent:build-debug-session-envelope-for-thread",
    "agent:build-session-envelope",
    "agent:build-session-envelope-for-thread",
    "agent:compute-session-token-count",
    "agent:create-session-hooks",
    "agent:create-session-message-logger",
    "agent:create-session-observability-sink",
    "agent:emit-fake-session-update",
    "agent:ingest-fake-session-update",
    "agent:ingest-fake-stream-update",
    "agent:list-debug-session-envelope-fields",
    "agent:list-session-tools",
    "agent:lookup-session-envelope-field",
    "agent:query-session-event-log",
    "agent:read-session-event-log",
    "agent:read-session-receipt",
    "agent:resolve-agent-event",
    "agent:resolve-profile-display-metadata",
    "agent:resolve-profile-order",
    "agent:resolve-profile-usage-stats",
    "agent:resolve-session-identity",
    "agent:resolve-session-state",
    "agent:restrict-session-prompt",
    "agent:replay-session-event-log",
    "agent:run-agent-turn",
    "agent:run-streaming-agent-turn",
    "agent:sanitize-session-prompt",
    "agent:sanitize-session-thinking",
    "agent:summarize-session-history",
    "agent:validate-session-context",
    "agent:write-session-event-log",
    "agent:write-session-receipt",
}

STABLE_PLUGIN_APIS: set[str] = {
    "app:config",
    "agent:background-job",
    "agent:conversation-context",
    "agent:core",
    "agent:debug-session",
    "agent:profile",
    "agent:run",
    "agent:runtime",
    "agent:session",
    "agent:session-event-log",
    "agent:session-state",
    "agent:streaming",
}


class PluginStatus:
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEPRECATED = "deprecated"
    REMOVED = "removed"


class APIReleaseLevel:
    STABLE = "stable"
    BETA = "beta"
    EXPERIMENTAL = "experimental"


PLUGIN_RELEASE_LEVEL: dict[str, str] = {}
