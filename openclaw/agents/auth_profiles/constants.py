"""Shared auth-profile constants."""

from openclaw.agents.auth_profiles.path_constants import AUTH_PROFILE_FILENAME

AUTH_STORE_VERSION = 1

CLAUDE_CLI_PROFILE_ID = "anthropic:claude-cli"
CODEX_CLI_PROFILE_ID = "openai:codex-cli"
OPENAI_CODEX_DEFAULT_PROFILE_ID = "openai:default"
MINIMAX_CLI_PROFILE_ID = "minimax-portal:minimax-cli"

OAUTH_REFRESH_LOCK_OPTIONS = {
    "retries": {
        "retries": 20,
        "factor": 2,
        "minTimeout": 100,
        "maxTimeout": 10_000,
        "randomize": True,
    },
    "stale": 180_000,
}

OAUTH_REFRESH_CALL_TIMEOUT_MS = 120_000
EXTERNAL_CLI_SYNC_TTL_MS = 15 * 60 * 1000

__all__ = [
    "AUTH_PROFILE_FILENAME",
    "AUTH_STORE_VERSION",
    "CLAUDE_CLI_PROFILE_ID",
    "CODEX_CLI_PROFILE_ID",
    "EXTERNAL_CLI_SYNC_TTL_MS",
    "MINIMAX_CLI_PROFILE_ID",
    "OAUTH_REFRESH_CALL_TIMEOUT_MS",
    "OAUTH_REFRESH_LOCK_OPTIONS",
    "OPENAI_CODEX_DEFAULT_PROFILE_ID",
]